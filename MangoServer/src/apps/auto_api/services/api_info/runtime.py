import hashlib
from copy import deepcopy
from pathlib import Path
from typing import Any

from django.conf import settings
from django.utils import timezone

from src.apps.auto_api.enums import ApiBodyTypeEnum, MethodEnum
from src.apps.auto_api.enums import ApiProtocolTypeEnum
from src.apps.auto_api.exceptions import (
    API_VERSION_API_INFO_NOT_FOUND,
    API_VERSION_API_INFO_VERSION_INVALID,
    AutoApiError,
)
from src.apps.auto_api.models import (
    ApiInfo,
    ApiInfoGrpcConfig,
    ApiInfoHttpConfig,
    ApiInfoMcpConfig,
    ApiInfoRelease,
    ApiInfoRevision,
    ApiInfoWebSocketConfig,
)
from src.apps.auto_api.schemas.config_fields import (
    API_INFO_CONFIG_DEFAULTS,
    API_INFO_CONFIG_FIELDS,
    default_api_info_config,
)
from src.apps.auto_api.schemas.version import ApiInfoRevisionPayloadModel
from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService


class ApiInfoRuntimeService:
    """把接口身份表和版本配置组装成运行时对象。"""

    @staticmethod
    def _materialize_descriptor_file(file_data) -> str | None:
        """Return a local descriptor path for both local and object storage backends."""
        if not file_data or not file_data.test_file:
            return None
        try:
            path = file_data.test_file.path
            if path:
                return path
        except (AttributeError, NotImplementedError, OSError):
            pass

        cache_root = Path(settings.BASE_DIR) / 'runtime' / 'grpc-descriptors'
        cache_root.mkdir(parents=True, exist_ok=True)
        version = str(getattr(file_data, 'update_time', '') or '')
        cache_key = hashlib.sha256(
            f'{file_data.id}:{file_data.test_file.name}:{version}'.encode('utf-8'),
        ).hexdigest()[:24]
        local_path = cache_root / f'{file_data.id}-{cache_key}.desc'
        if not local_path.exists():
            temporary_path = local_path.with_suffix('.tmp')
            try:
                with file_data.test_file.open('rb') as source, temporary_path.open('wb') as target:
                    while True:
                        chunk = source.read(1024 * 1024)
                        if not chunk:
                            break
                        target.write(chunk)
                temporary_path.replace(local_path)
            finally:
                if temporary_path.exists():
                    temporary_path.unlink()
        return str(local_path)

    @classmethod
    def current_payload(cls, api_info: ApiInfo) -> dict[str, Any]:
        payload = {}
        for field_name in API_INFO_CONFIG_FIELDS:
            if field_name == 'mcp_binding':
                value = cls.capture_mcp_binding(api_info)
            elif field_name == 'grpc_binding':
                value = cls.capture_grpc_binding(api_info)
            else:
                value = getattr(api_info, field_name, API_INFO_CONFIG_DEFAULTS.get(field_name))
            payload[field_name] = deepcopy(value)
        payload.update(cls.capture_protocol_flat_payload(api_info))
        payload['protocol_config'] = cls.capture_protocol_config(api_info)
        return cls.normalize_payload(payload)

    @classmethod
    def merge_editing_payload(
            cls,
            api_info: ApiInfo,
            patch: dict[str, Any] | None,
    ) -> dict[str, Any]:
        payload = cls.current_payload(api_info)
        # protocol_config 是由各协议编辑态表生成的快照。部分更新必须以扁平字段
        # 为准并在保存后重新生成，否则旧快照会在 normalize_payload 中覆盖新值。
        payload.pop('protocol_config', None)
        payload.update(deepcopy(patch or {}))
        return cls.normalize_payload(payload)

    @classmethod
    def normalize_payload(cls, payload: dict[str, Any] | None) -> dict[str, Any]:
        source = payload or {}
        if 'api_info' in source:
            source = ApiInfoRevisionPayloadModel.from_payload(source).api_info
        normalized = default_api_info_config()
        for field in API_INFO_CONFIG_FIELDS:
            if field in source:
                normalized[field] = deepcopy(source[field])
        protocol_config = deepcopy(source.get('protocol_config'))
        if isinstance(protocol_config, dict):
            cls.apply_protocol_config_to_payload(normalized, protocol_config)
            normalized['protocol_config'] = protocol_config
        normalized['posterior_json_path'] = deepcopy(
            source.get('posterior_json_path', source.get('posterior_response', normalized['posterior_json_path']))
        )
        normalized['posterior_re'] = deepcopy(
            source.get('posterior_re', source.get('posterior_response_text', normalized['posterior_re']))
        )
        return normalized

    @classmethod
    def capture_revision_payload(cls, api_info: ApiInfo) -> dict[str, Any]:
        return ApiInfoRevisionPayloadModel(
            api_info=cls.capture_runtime_payload(api_info),
            runtime={},
        ).model_dump()

    @classmethod
    def apply_payload(cls, api_info: ApiInfo, payload: dict[str, Any]) -> ApiInfo:
        source_payload = payload or {}
        payload = cls.normalize_payload(payload)
        setattr(api_info, '_protocol_config_snapshot', deepcopy(source_payload.get('protocol_config')))
        for field in API_INFO_CONFIG_FIELDS:
            if field == 'mcp_binding':
                setattr(api_info, '_mcp_binding_snapshot', deepcopy(payload.get(field)))
                continue
            if field == 'grpc_binding':
                setattr(api_info, '_grpc_binding_snapshot', deepcopy(payload.get(field)))
                continue
            setattr(api_info, field, deepcopy(payload[field]))
        return api_info

    @classmethod
    def resolve_payload(
            cls,
            api_info_id: int,
            *,
            allow_draft: bool = True,
            revision_id: int | None = None,
            release_id: int | None = None,
    ) -> tuple[dict[str, Any], ApiInfoRevision | None]:
        if revision_id is not None:
            revision = ApiInfoRevision.objects.filter(id=revision_id, api_info_id=api_info_id).first()
            if revision:
                ApiInfoRevisionService.verify_revision(revision, executable=True)
                return cls.normalize_payload(
                    ApiInfoRevisionPayloadModel.from_payload(revision.payload).api_info,
                ), revision
            raise AutoApiError(API_VERSION_API_INFO_VERSION_INVALID)

        if release_id is not None:
            release = ApiInfoRelease.objects.filter(id=release_id, api_info_id=api_info_id).select_related(
                'revision').first()
            if release:
                ApiInfoRevisionService.verify_revision(release.revision, executable=True)
                return cls.normalize_payload(
                    ApiInfoRevisionPayloadModel.from_payload(release.revision.payload).api_info,
                ), release.revision
            raise AutoApiError(API_VERSION_API_INFO_VERSION_INVALID)

        api_info = ApiInfo.objects.filter(id=api_info_id).first()
        if api_info is None:
            raise AutoApiError(API_VERSION_API_INFO_NOT_FOUND, value=(api_info_id,))
        base_revision = ApiInfoRevision.objects.filter(api_info_id=api_info_id).order_by('-revision_no').first()
        return cls.current_payload(api_info), base_revision

    @classmethod
    def resolve_runtime(
            cls,
            api_info_id: int,
            *,
            allow_draft: bool = True,
            revision_id: int | None = None,
            release_id: int | None = None,
    ) -> ApiInfo:
        api_info = ApiInfo.objects.filter(id=api_info_id).first()
        if api_info is None:
            raise AutoApiError(API_VERSION_API_INFO_NOT_FOUND, value=(api_info_id,))
        payload, _revision = cls.resolve_payload(
            api_info_id,
            allow_draft=allow_draft,
            revision_id=revision_id,
            release_id=release_id,
        )
        return cls.apply_payload(api_info, payload)

    @classmethod
    def capture_runtime_payload(cls, api_info: ApiInfo) -> dict[str, Any]:
        payload = {}
        for field, default in API_INFO_CONFIG_DEFAULTS.items():
            if field == 'mcp_binding':
                payload[field] = cls.capture_mcp_binding(api_info)
            elif field == 'grpc_binding':
                payload[field] = cls.capture_grpc_binding(api_info)
            else:
                payload[field] = deepcopy(getattr(api_info, field, default))
        payload.update(cls.capture_protocol_flat_payload(api_info))
        payload['protocol_config'] = cls.capture_protocol_config(api_info)
        return cls.normalize_payload(payload)

    @classmethod
    def capture_protocol_flat_payload(cls, api_info: ApiInfo) -> dict[str, Any]:
        protocol_type = api_info.protocol_type or ApiProtocolTypeEnum.HTTP.value
        if protocol_type in (ApiProtocolTypeEnum.HTTP.value, ApiProtocolTypeEnum.SSE.value):
            config = ApiInfoHttpConfig.objects.filter(api_info_id=api_info.id).first()
            if config is None:
                return {}
            return {
                'method': config.method,
                'url': config.url,
                'headers': deepcopy(config.headers),
                'params': config.params,
                'is_text_params': config.is_text_params,
                'body_type': config.body_type,
                'body_config': deepcopy(config.body_config),
                'sse_config': deepcopy(config.sse_config),
            }
        if protocol_type == ApiProtocolTypeEnum.WEBSOCKET.value:
            config = ApiInfoWebSocketConfig.objects.filter(api_info_id=api_info.id).first()
            if config is None:
                return {}
            return {
                'method': MethodEnum.WEBSOCKET_CONNECT.value,
                'url': config.url,
                'headers': deepcopy(config.headers),
                'params': config.params,
                'is_text_params': config.is_text_params,
                'body_type': ApiBodyTypeEnum.JSON.value,
                'body_config': deepcopy(config.body_config),
                'sse_config': None,
            }
        return {}

    @classmethod
    def capture_protocol_config(cls, api_info: ApiInfo) -> dict[str, Any]:
        protocol_type = api_info.protocol_type or ApiProtocolTypeEnum.HTTP.value
        config: dict[str, Any] = {'type': protocol_type, 'config': {}}
        if protocol_type in (ApiProtocolTypeEnum.HTTP.value, ApiProtocolTypeEnum.SSE.value):
            flat = cls.capture_protocol_flat_payload(api_info)
            config['config'] = flat or {
                'method': MethodEnum.GET.value,
                'url': api_info.url,
                'headers': None,
                'params': None,
                'is_text_params': 1,
                'body_type': ApiBodyTypeEnum.NONE.value,
                'body_config': None,
                'sse_config': None,
            }
        elif protocol_type == ApiProtocolTypeEnum.WEBSOCKET.value:
            flat = cls.capture_protocol_flat_payload(api_info)
            config['config'] = flat or {
                'method': MethodEnum.WEBSOCKET_CONNECT.value,
                'url': api_info.url,
                'headers': None,
                'params': None,
                'is_text_params': 1,
                'body_type': ApiBodyTypeEnum.JSON.value,
                'body_config': None,
                'sse_config': None,
            }
        elif protocol_type == ApiProtocolTypeEnum.MCP.value:
            mcp_binding = cls.capture_mcp_binding(api_info)
            mcp_config = deepcopy((mcp_binding or {}).get('mcp_config')) or {}
            config['config'] = {
                'method': MethodEnum.MCP_CALL.value,
                'body_type': ApiBodyTypeEnum.JSON.value,
                'body_config': deepcopy(mcp_config.get('body_config')) or {'source_type': 'value', 'body': {}},
                'mcp_config': mcp_config,
                'mcp_binding': mcp_binding,
            }
        elif protocol_type == ApiProtocolTypeEnum.GRPC.value:
            grpc_binding = cls.capture_grpc_binding(api_info)
            grpc_config = deepcopy((grpc_binding or {}).get('grpc_config')) or {}
            config['config'] = {
                'method': MethodEnum.GRPC_CALL.value,
                'body_type': ApiBodyTypeEnum.JSON.value,
                'body_config': deepcopy(grpc_config.get('body_config')) or {'source_type': 'value', 'body': {}},
                'grpc_config': grpc_config,
                'grpc_binding': grpc_binding,
            }
        return config

    @classmethod
    def apply_protocol_config_to_payload(cls, payload: dict[str, Any], protocol_config: dict[str, Any]):
        protocol_type = protocol_config.get('type') or payload.get('protocol_type') or ApiProtocolTypeEnum.HTTP.value
        config = protocol_config.get('config') if isinstance(protocol_config.get('config'), dict) else {}
        payload['protocol_type'] = protocol_type
        if protocol_type in (ApiProtocolTypeEnum.HTTP.value, ApiProtocolTypeEnum.SSE.value,
                             ApiProtocolTypeEnum.WEBSOCKET.value):
            for field in ('method', 'url', 'headers', 'params', 'is_text_params', 'body_type', 'body_config',
                          'sse_config'):
                if field in config:
                    payload[field] = deepcopy(config.get(field))
            if protocol_type == ApiProtocolTypeEnum.WEBSOCKET.value:
                payload['method'] = MethodEnum.WEBSOCKET_CONNECT.value
                payload['body_type'] = ApiBodyTypeEnum.JSON.value
                payload['sse_config'] = None
        elif protocol_type == ApiProtocolTypeEnum.MCP.value:
            payload['method'] = MethodEnum.MCP_CALL.value
            payload['body_type'] = ApiBodyTypeEnum.JSON.value
            if 'body_config' in config:
                payload['body_config'] = deepcopy(config.get('body_config'))
            if 'mcp_config' in config:
                payload['mcp_config'] = deepcopy(config.get('mcp_config'))
            if 'mcp_binding' in config:
                payload['mcp_binding'] = deepcopy(config.get('mcp_binding'))
        elif protocol_type == ApiProtocolTypeEnum.GRPC.value:
            payload['method'] = MethodEnum.GRPC_CALL.value
            payload['body_type'] = ApiBodyTypeEnum.JSON.value
            if 'body_config' in config:
                payload['body_config'] = deepcopy(config.get('body_config'))
            if 'grpc_config' in config:
                payload['grpc_config'] = deepcopy(config.get('grpc_config'))
            if 'grpc_binding' in config:
                grpc_binding = deepcopy(config.get('grpc_binding'))
                if isinstance(grpc_binding, dict) and 'grpc_config' not in grpc_binding:
                    grpc_binding['grpc_config'] = deepcopy(config.get('grpc_config'))
                payload['grpc_binding'] = grpc_binding

    @classmethod
    def sync_protocol_config(cls, api_info: ApiInfo):
        protocol_type = api_info.protocol_type or ApiProtocolTypeEnum.HTTP.value
        if protocol_type != ApiProtocolTypeEnum.MCP.value:
            ApiInfoMcpConfig.objects.filter(api_info=api_info).delete()
        if protocol_type != ApiProtocolTypeEnum.GRPC.value:
            ApiInfoGrpcConfig.objects.filter(api_info=api_info).delete()
        if protocol_type == ApiProtocolTypeEnum.MCP.value:
            cls.restore_mcp_binding(api_info)
        if protocol_type in (ApiProtocolTypeEnum.HTTP.value, ApiProtocolTypeEnum.SSE.value):
            ApiInfoHttpConfig.objects.update_or_create(
                api_info=api_info,
                defaults={
                    'method': getattr(api_info, 'method', MethodEnum.GET.value),
                    'url': getattr(api_info, 'url', ''),
                    'headers': deepcopy(getattr(api_info, 'headers', None)),
                    'params': getattr(api_info, 'params', None),
                    'is_text_params': getattr(api_info, 'is_text_params', 1),
                    'body_type': getattr(api_info, 'body_type', ApiBodyTypeEnum.NONE.value),
                    'body_config': deepcopy(getattr(api_info, 'body_config', None)),
                    'sse_config': deepcopy(getattr(api_info, 'sse_config', None)),
                },
            )
            ApiInfoWebSocketConfig.objects.filter(api_info=api_info).delete()
        elif protocol_type == ApiProtocolTypeEnum.WEBSOCKET.value:
            ApiInfoWebSocketConfig.objects.update_or_create(
                api_info=api_info,
                defaults={
                    'url': getattr(api_info, 'url', ''),
                    'headers': deepcopy(getattr(api_info, 'headers', None)),
                    'params': getattr(api_info, 'params', None),
                    'is_text_params': getattr(api_info, 'is_text_params', 1),
                    'body_config': deepcopy(getattr(api_info, 'body_config', None)),
                },
            )
            ApiInfoHttpConfig.objects.filter(api_info=api_info).delete()

    @classmethod
    def capture_mcp_binding(cls, api_info):
        if api_info.protocol_type != ApiProtocolTypeEnum.MCP.value:
            return None
        config = ApiInfoMcpConfig.objects.filter(api_info_id=api_info.id).first()
        if not config or not config.binding_snapshot:
            return None
        snapshot = deepcopy(config.binding_snapshot)
        snapshot.update({"mcp_config": deepcopy(config.mcp_config), "input_schema": deepcopy(config.input_schema),
                         "output_schema": deepcopy(config.output_schema), "schema_hash": config.schema_hash})
        return snapshot

    @staticmethod
    def format_snapshot_time(value):
        if value is None:
            return None
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        return timezone.localtime(value).strftime('%Y-%m-%d %H:%M:%S')



    @staticmethod
    def mcp_schema_hash(input_schema: dict | None, output_schema: dict | None) -> str:
        import hashlib
        import json

        payload = json.dumps(
            {'input_schema': input_schema or {}, 'output_schema': output_schema or {}},
            ensure_ascii=False,
            sort_keys=True,
            separators=(',', ':'),
        )
        return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"

    @classmethod
    def restore_mcp_binding(cls, api_info):
        from pydantic import ValidationError
        from src.apps.auto_api.schemas.mcp import McpBindingDefinition
        from src.apps.auto_api.exceptions import MCP_API_API_INFO_BINDING_INVALID
        snapshot = getattr(api_info, "_mcp_binding_snapshot", None)
        if api_info.protocol_type != ApiProtocolTypeEnum.MCP.value:
            ApiInfoMcpConfig.objects.filter(api_info=api_info).delete()
            return
        try:
            snapshot = McpBindingDefinition.model_validate(snapshot).model_dump()
        except ValidationError as exc:
            raise AutoApiError(MCP_API_API_INFO_BINDING_INVALID) from exc
        ApiInfoMcpConfig.objects.update_or_create(api_info=api_info, defaults={
            "binding_snapshot": {key: deepcopy(value) for key, value in snapshot.items()
                                 if key not in {"mcp_config", "input_schema", "output_schema", "schema_hash"}},
            "mcp_config": deepcopy(snapshot.get("mcp_config")),
            "input_schema": deepcopy(snapshot.get("input_schema")),
            "output_schema": deepcopy(snapshot.get("output_schema")),
            "schema_hash": snapshot.get("schema_hash") or cls.mcp_schema_hash(snapshot.get("input_schema"), snapshot.get("output_schema"))})

    @classmethod
    def capture_grpc_binding(cls, api_info: ApiInfo) -> dict[str, Any] | None:
        if api_info.protocol_type != ApiProtocolTypeEnum.GRPC.value:
            return None
        config = (
            ApiInfoGrpcConfig.objects
            .filter(api_info_id=api_info.id)
            .select_related(
                'grpc_service',
                'grpc_service__descriptor_file',
                'grpc_method',
            )
            .first()
        )
        if config is None:
            return None
        service = config.grpc_service
        method = config.grpc_method
        descriptor_path = None
        if service.descriptor_file and service.descriptor_file.test_file:
            descriptor_path = cls._materialize_descriptor_file(service.descriptor_file)
        return {
            'service_id': service.id,
            'service_name': service.name,
            'package': service.package,
            'grpc_service_name': service.service_name,
            'method_id': method.id,
            'method_name': method.name,
            'full_method': config.full_method,
            'request_message': config.request_message,
            'response_message': config.response_message,
            'client_streaming': method.client_streaming,
            'server_streaming': method.server_streaming,
            'proto_hash': config.proto_hash or service.proto_content_hash,
            'descriptor_file_id': service.descriptor_file_id,
            'descriptor_file_path': descriptor_path,
            'tls_enabled': service.tls_enabled,
            'request_json_schema': deepcopy(config.request_json_schema or method.request_json_schema),
            'response_json_schema': deepcopy(config.response_json_schema or method.response_json_schema),
            'grpc_config': deepcopy(config.grpc_config) if config else None,
        }

    @classmethod
    def restore_grpc_binding(cls, api_info: ApiInfo):
        snapshot = getattr(api_info, '_grpc_binding_snapshot', None)
        if api_info.protocol_type != ApiProtocolTypeEnum.GRPC.value:
            ApiInfoGrpcConfig.objects.filter(api_info=api_info).delete()
            return
        if not isinstance(snapshot, dict) or not snapshot.get('method_id'):
            ApiInfoGrpcConfig.objects.filter(api_info=api_info).delete()
            return
        from src.apps.auto_api.models import GrpcMethodDefinition

        method = GrpcMethodDefinition.objects.select_related('service').filter(id=snapshot.get('method_id')).first()
        if method is None:
            ApiInfoGrpcConfig.objects.filter(api_info=api_info).delete()
            return
        defaults = {
            'grpc_service': method.service,
            'grpc_method': method,
            'full_method': snapshot.get('full_method') or method.full_method,
            'request_message': snapshot.get('request_message') or method.request_message,
            'response_message': snapshot.get('response_message') or method.response_message,
            'proto_hash': snapshot.get('proto_hash') or method.service.proto_content_hash,
            'request_json_schema': snapshot.get('request_json_schema') or method.request_json_schema,
            'response_json_schema': snapshot.get('response_json_schema') or method.response_json_schema,
        }
        ApiInfoGrpcConfig.objects.update_or_create(
            api_info=api_info,
            defaults={
                **defaults,
                'grpc_config': deepcopy(snapshot.get('grpc_config')),
            },
        )
