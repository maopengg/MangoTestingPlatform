from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from django.db import models
from mangotools.enums import StatusEnum

from src.apps.auto_api.exceptions import (
    API_VERSION_API_INFO_REVISION_NOT_FOUND,
    API_VERSION_CASE_REVISION_INVALID,
    AutoApiError,
)
from src.apps.auto_api.models import (
    ApiCase,
    ApiCaseDetailed,
    ApiCaseDetailedParameter,
    ApiHeaders,
    ApiInfo,
    ApiInfoRelease,
)
from src.apps.auto_api.schemas.config_fields import (
    API_CASE_CONFIG_FIELDS,
    API_INFO_CONFIG_DEFAULTS,
    default_api_case_config,
)
from src.apps.auto_api.schemas.version import ApiCaseRevisionPayloadModel
from src.apps.auto_api.services.config.version import ApiConfigSnapshotService


@dataclass(frozen=True)
class ApiCasePublicationState:
    publication_status: str
    current_revision_id: int | None
    current_revision_no: int | None
    published_release_id: int | None
    published_revision_id: int | None
    published_version_label: str | None
    prepublished_revision_id: int | None
    prepublished_revision_no: int | None
    has_unpublished_changes: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ApiCaseExecutionSelection:
    case_id: int
    case_revision_id: int | None
    case_revision_no: int | None
    case_release_id: int | None
    version_label: str | None
    checksum: str | None
    execution_source: str = 'published'

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ApiCaseExecutionAggregate:
    revision_id: int | None
    revision_no: int | None
    checksum: str
    api_case: ApiCase
    steps: tuple[ApiCaseDetailed, ...]
    api_revision_dependencies: tuple[dict[str, Any], ...]
    data_factory_configs: tuple[dict[str, Any], ...]
    _parameters_by_step: Mapping[int, tuple[ApiCaseDetailedParameter, ...]]

    def parameters_for_step(self, step: ApiCaseDetailed) -> tuple[ApiCaseDetailedParameter, ...]:
        return self._parameters_by_step.get(step.id, ())

    def data_factory_configs_for(self, source_type: int, source_id: int) -> tuple[dict[str, Any], ...]:
        return tuple(
            deepcopy(config)
            for config in self.data_factory_configs
            if config.get('source_type') == source_type and config.get('source_id') == source_id
        )


class ApiExecutableSnapshotService:
    """生成可执行版本快照；运行状态不进入 payload，配置值按原文冻结。"""

    SNAPSHOT_SCHEMA_VERSION = 2
    CASE_RUNTIME_FIELDS = {
        'create_time',
        'update_time',
        'status',
        'scenario_layer',
        'scenario_type',
        'scenario_tags',
    }
    STEP_RUNTIME_FIELDS = {'create_time', 'update_time', 'status', 'error_message'}
    PARAMETER_RUNTIME_FIELDS = {'create_time', 'update_time', 'status'}
    API_RUNTIME_FIELDS = {'create_time', 'update_time', 'status'}

    @classmethod
    def serialize_model(cls, instance, excluded_fields: set[str]) -> dict[str, Any]:
        data = {}
        for field in instance._meta.concrete_fields:
            if field.name in excluded_fields:
                continue
            if isinstance(field, models.ForeignKey):
                value = getattr(instance, field.attname)
            else:
                value = getattr(instance, field.name)
            data[field.name] = ApiConfigSnapshotService.to_jsonable(value)
        return data

    @classmethod
    def capture_api_info(cls, api_info: ApiInfo) -> dict[str, Any]:
        payload = cls.serialize_model(api_info, cls.API_RUNTIME_FIELDS)
        for field, default in API_INFO_CONFIG_DEFAULTS.items():
            payload[field] = ApiConfigSnapshotService.to_jsonable(getattr(api_info, field, default))
        return payload

    @classmethod
    def capture_case(
            cls,
            api_case: ApiCase,
            api_revision_resolver,
            *,
            require_published_api_revisions: bool = True,
    ) -> dict[str, Any]:
        api_case_payload = cls.serialize_model(api_case, cls.CASE_RUNTIME_FIELDS)
        api_case_payload.update(cls.current_case_config(api_case.id, api_case.project_product_id))
        if not api_case_payload.get('callback_checks'):
            # 未配置的新字段不改变历史修订 checksum。
            api_case_payload.pop('callback_checks', None)
        (
            resolved_front_headers,
            missing_front_header_ids,
        ) = cls.resolve_case_headers(api_case, project_product_id=api_case.project_product_id)
        step_payloads = []
        api_revision_dependencies = []
        steps = ApiCaseDetailed.objects.filter(case_id=api_case.id).select_related(
            'api_info',
            'pinned_api_info_revision',
        ).order_by(
            'case_sort',
            'id',
        )
        for step in steps:
            api_revision = step.pinned_api_info_revision or api_revision_resolver(step.api_info)
            if api_revision.api_info_id != step.api_info_id:
                raise AutoApiError(API_VERSION_API_INFO_REVISION_NOT_FOUND)
            from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService
            ApiInfoRevisionService.verify_revision(api_revision, executable=True)
            if require_published_api_revisions and not ApiInfoRelease.objects.filter(
                    api_info_id=api_revision.api_info_id,
                    revision_id=api_revision.id,
                    status=ApiInfoRelease.STATUS_PUBLISHED,
            ).exists():
                raise AutoApiError(API_VERSION_CASE_REVISION_INVALID,
                                   value=(f'步骤 {step.id} 绑定的接口版本未发布',),
                                   )
            logical_id = f'step-{step.id}'
            step_payload = cls.serialize_model(step, cls.STEP_RUNTIME_FIELDS)
            if not step.execution_config:
                # 默认普通步骤保持旧快照形状，避免升级后全部用例被误判为有未发布变更。
                step_payload.pop('execution_config', None)
            step_payload['logical_id'] = logical_id
            step_payload['api_info_id'] = step.api_info_id
            step_payload['api_info_revision_id'] = api_revision.id
            step_payload['api_info_snapshot'] = {
                'id': step.api_info_id,
                'name': step.api_info.name,
                'project_product_id': step.api_info.project_product_id,
                'module_id': step.api_info.module_id,
                'revision_id': api_revision.id,
                'revision_no': api_revision.revision_no,
                'snapshot_schema_version': api_revision.snapshot_schema_version,
                'checksum': api_revision.checksum,
                'payload': deepcopy(api_revision.payload),
            }
            step_payload['api_case_detailed_parameter'] = []
            parameters = ApiCaseDetailedParameter.objects.filter(case_detailed_id=step.id).order_by('id')
            for parameter in parameters:
                parameter_payload = cls.serialize_model(parameter, cls.PARAMETER_RUNTIME_FIELDS)
                (
                    parameter_payload['resolved_headers'],
                    parameter_payload['missing_header_ids'],
                ) = cls.resolve_parameter_headers(parameter)
                parameter_payload['gray_configs'] = []
                step_payload['api_case_detailed_parameter'].append(parameter_payload)
            step_payloads.append(step_payload)
            api_revision_dependencies.append({
                'step_logical_id': logical_id,
                'api_info_id': api_revision.api_info_id,
                'api_info_revision_id': api_revision.id,
                'checksum': api_revision.checksum,
            })
        data_factory_configs = ApiConfigSnapshotService.serialize_data_factory_configs(api_case.id)
        unsupported_dependency_types = []
        payload = ApiCaseRevisionPayloadModel(
            api_case=api_case_payload,
            api_case_detailed=step_payloads,
            runtime={
                'resolved_front_headers': resolved_front_headers,
                'missing_front_header_ids': missing_front_header_ids,
                'gray_configs': [],
                'dependency_freeze_level': 'case_api_snapshot_v3',
                'unsupported_dependency_types': unsupported_dependency_types,
            },
            dependencies={
                'data_factory_configs': data_factory_configs,
                'api_revision_dependencies': api_revision_dependencies,
            },
        ).model_dump()
        return payload

    @classmethod
    def current_case_config(cls, case_id: int, project_product_id: int | None = None) -> dict[str, Any]:
        config = default_api_case_config()
        api_case = ApiCase.objects.filter(id=case_id).first()
        if api_case is not None:
            for field in API_CASE_CONFIG_FIELDS:
                config[field] = ApiConfigSnapshotService.to_jsonable(getattr(api_case, field))
            return config
        if project_product_id is not None:
            config['front_headers'] = list(
                ApiHeaders.objects.filter(
                    project_product_id=project_product_id,
                    status=StatusEnum.SUCCESS.value,
                ).values_list('id', flat=True)
            )
        return config

    @classmethod
    def apply_case_execution_config(cls, api_case: ApiCase, payload: dict[str, Any]):
        if isinstance(payload, dict) and 'api_case' in payload:
            payload = payload.get('api_case') or {}
        for field, default in default_api_case_config().items():
            setattr(api_case, field, deepcopy(payload.get(field, default)))
        return api_case

    @classmethod
    def resolve_case_headers(cls, api_case: ApiCase, project_product_id: int | None = None) -> tuple[
        dict[str, str], list[Any]]:
        front_headers = getattr(api_case, 'front_headers', None)
        if front_headers:
            return cls.resolve_selected_headers(front_headers)
        project_product_id = project_product_id or getattr(api_case, 'project_product_id', None)
        queryset = ApiHeaders.objects.filter(
            project_product_id=project_product_id,
            status=StatusEnum.SUCCESS.value,
        )
        return {header.key: header.value for header in queryset}, []

    @classmethod
    def resolve_parameter_headers(
            cls,
            parameter: ApiCaseDetailedParameter,
    ) -> tuple[dict[str, str] | None, list[Any]]:
        if not parameter.headers:
            return None, []
        resolved, missing_ids = cls.resolve_selected_headers(parameter.headers)
        return resolved, missing_ids

    @staticmethod
    def resolve_selected_headers(header_ids: list[Any]) -> tuple[dict[str, str], list[Any]]:
        normalized_ids = []
        invalid_ids = []
        for header_id in dict.fromkeys(header_ids):
            try:
                normalized_ids.append(int(header_id))
            except (TypeError, ValueError):
                invalid_ids.append(header_id)
        headers = list(ApiHeaders.objects.filter(id__in=normalized_ids))
        found_ids = {header.id for header in headers}
        missing_ids = invalid_ids + [
            header_id
            for header_id in normalized_ids
            if header_id not in found_ids
        ]
        return {header.key: header.value for header in headers}, missing_ids

    @staticmethod
    def has_active_gray_configs(case_id: int) -> bool:
        from src.apps.gray_config.enums import GrayCaseTypeEnum
        from src.apps.gray_config.models import AutomationCaseGrayConfig

        return AutomationCaseGrayConfig.objects.filter(
            case_type=GrayCaseTypeEnum.API.value,
            status=StatusEnum.SUCCESS.value,
        ).filter(
            models.Q(api_case_id=case_id) |
            models.Q(api_case_detailed__case_id=case_id) |
            models.Q(api_case_detailed_parameter__case_detailed__case_id=case_id)
        ).exists()

    @staticmethod
    def hydrate_model(model_class, payload: dict[str, Any]):
        values = {}
        for field in model_class._meta.concrete_fields:
            if field.name not in payload:
                continue
            key = field.attname if isinstance(field, models.ForeignKey) else field.name
            values[key] = deepcopy(payload[field.name])
        return model_class(**values)
