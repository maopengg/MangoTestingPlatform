import hashlib
# -*- coding: utf-8 -*-
import json
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

import jsonschema
import time

from src.apps.auto_api.enums import ApiProtocolTypeEnum
from src.apps.auto_api.enums.execution_trace import ApiCaseTraceStepType
from src.apps.auto_api.exceptions import (
    AUTO_API_PROTOCOLS_GRPC_JSON_INVALID,
    AUTO_API_PROTOCOLS_GRPC_JSON_INVALID_CODE_JSON_INVALID,
    AutoApiError,
    GRPC_API_API_INFO_BINDING_REQUIRED,
    GRPC_API_EXECUTOR_API_INFO_EXECUTION_UNSUPPORTED,
    GRPC_API_JSON_PARAMETER_TYPE_INVALID,
    GRPC_API_INVALID,
    GRPC_API_FILE_INVALID,
    GRPC_API_API_INFO_REQUEST_RESPONSE_BINDING_NOT_FOUND,
    GRPC_API_REQUEST_FAILED,
    GRPC_API_FAILED,
)
from src.apps.auto_api.schemas.execution import ApiExecutionRequest, ApiExecutionResponse
from src.apps.auto_api.services.protocols.utils import positive_int
from src.common.logging import log

try:
    import grpc
    from google.protobuf import descriptor_pb2, descriptor_pool, json_format, message_factory
except ImportError:  # pragma: no cover - 依赖缺失时运行时抛业务错误
    grpc = None
    descriptor_pb2 = None
    descriptor_pool = None
    json_format = None
    message_factory = None


class GrpcDescriptorLoader:
    """从 FileDescriptorSet 文件加载动态 protobuf message。"""

    @classmethod
    @lru_cache(maxsize=64)
    def load_pool(cls, descriptor_path: str):
        if descriptor_pb2 is None or descriptor_pool is None:
            raise AutoApiError(GRPC_API_INVALID)
        try:
            with open(descriptor_path, 'rb') as file:
                content = file.read()
        except Exception as error:
            raise AutoApiError(GRPC_API_FILE_INVALID, value=(f'无法读取descriptor文件：{error}',)) from error
        try:
            file_set = descriptor_pb2.FileDescriptorSet()
            file_set.ParseFromString(content)
            pool = descriptor_pool.DescriptorPool()
            pending = list(file_set.file)
            last_error = None
            while pending:
                remaining = []
                added = 0
                for file_proto in pending:
                    try:
                        pool.Add(file_proto)
                        added += 1
                    except Exception as error:
                        last_error = error
                        remaining.append(file_proto)
                if not remaining:
                    break
                if added == 0:
                    names = ', '.join(item.name for item in remaining[:5])
                    raise AutoApiError(GRPC_API_FILE_INVALID,
                                       value=(f'descriptor依赖无法解析：{names}；{last_error}',),
                                       )
                pending = remaining
            return pool
        except Exception as error:
            raise AutoApiError(GRPC_API_FILE_INVALID,
                               value=(f'descriptor不是合法FileDescriptorSet：{error}',)) from error

    @classmethod
    def message_class(cls, pool, message_name: str):
        try:
            descriptor = pool.FindMessageTypeByName(message_name)
        except Exception as error:
            raise AutoApiError(GRPC_API_FILE_INVALID, value=(f'未找到Message：{message_name}',)) from error
        if hasattr(message_factory, 'GetMessageClass'):
            return message_factory.GetMessageClass(descriptor)
        return message_factory.MessageFactory(pool).GetPrototype(descriptor)


class GrpcProtocolClient:
    """API 自动化中的 gRPC 一元调用执行器。"""

    RESERVED_METADATA = {
        'content-type',
        'te',
        'grpc-timeout',
        'grpc-encoding',
        'grpc-accept-encoding',
        'user-agent',
    }

    def __init__(self, *, timeout, channel_manager=None):
        self.timeout = timeout
        self.channel_manager = channel_manager

    def request(self, request_data: ApiExecutionRequest, prepared_body, start_time: float) -> ApiExecutionResponse:
        if grpc is None or json_format is None:
            raise AutoApiError(GRPC_API_INVALID)
        if not request_data.grpc_full_method:
            raise AutoApiError(GRPC_API_API_INFO_BINDING_REQUIRED)
        grpc_config = request_data.grpc_config or {}
        if grpc_config.get('client_streaming') or grpc_config.get('server_streaming'):
            raise AutoApiError(GRPC_API_EXECUTOR_API_INFO_EXECUTION_UNSUPPORTED, value=(request_data.grpc_full_method,))
        arguments = prepared_body.request_body
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise AutoApiError(GRPC_API_JSON_PARAMETER_TYPE_INVALID, value=(type(arguments).__name__,))
        if grpc_config.get('validate_request_schema'):
            self.validate_json_schema(arguments, grpc_config.get('request_json_schema'), 'gRPC请求Message')
        descriptor_path = grpc_config.get('descriptor_file_path')
        if not descriptor_path:
            raise AutoApiError(GRPC_API_FILE_INVALID,
                               value=('未绑定descriptor文件，请先在gRPC服务定义中上传descriptor',))
        request_message = request_data.grpc_request_message
        response_message = request_data.grpc_response_message
        pool = GrpcDescriptorLoader.load_pool(descriptor_path)
        try:
            request_cls = GrpcDescriptorLoader.message_class(pool, request_message)
            response_cls = GrpcDescriptorLoader.message_class(pool, response_message)
        except AutoApiError:
            raise
        except Exception as error:
            raise AutoApiError(GRPC_API_API_INFO_REQUEST_RESPONSE_BINDING_NOT_FOUND,
                               value=(request_message, response_message)) from error
        try:
            request_message_obj = request_cls()
            json_format.ParseDict(arguments, request_message_obj,
                                  ignore_unknown_fields=bool(grpc_config.get('ignore_unknown_fields')))
        except Exception as error:
            raise AutoApiError(GRPC_API_REQUEST_FAILED, value=(str(error),)) from error

        timeout = positive_int(grpc_config.get('timeout_seconds') or self.timeout or 60, 'gRPC调用超时时间')
        metadata = self.business_metadata(request_data.headers)
        initial_metadata = {}
        trailing_metadata = {}
        status_code = 'OK'
        status_details = ''
        response_json: dict[str, Any] | None = None
        text = ''
        target = self.target_from_config(grpc_config, request_data.url)
        call_step = self._start_call_trace(request_data, target, timeout, metadata)
        channel = None
        try:
            channel = self._get_channel(target, grpc_config)
            stub = channel.unary_unary(
                request_data.grpc_full_method,
                request_serializer=request_message_obj.SerializeToString,
                response_deserializer=response_cls.FromString,
            )
            response_message_obj, call = stub.with_call(request_message_obj, timeout=timeout, metadata=metadata)
            initial_metadata = self.metadata_to_dict(call.initial_metadata())
            trailing_metadata = self.metadata_to_dict(call.trailing_metadata())
            code = call.code()
            status_code = code.name if code else 'OK'
            status_details = call.details() or ''
            response_json = self.message_to_dict(
                response_message_obj,
                include_default_values=bool(grpc_config.get('include_default_values')),
            )
            if grpc_config.get('validate_response_schema'):
                self.validate_json_schema(response_json, grpc_config.get('response_json_schema'), 'gRPC响应Message')
            text = json.dumps(response_json, ensure_ascii=False)
            self._finish_call_trace(call_step, {
                'grpc_status_code': status_code,
                'initial_metadata_keys': list(initial_metadata.keys()),
                'trailing_metadata_keys': list(trailing_metadata.keys()),
                'response_json_keys': list(response_json.keys()) if isinstance(response_json, dict) else None,
                'response_text_size': len(text),
            })
        except grpc.RpcError as error:
            code = error.code()
            status_code = code.name if code else 'UNKNOWN'
            status_details = error.details() or ''
            trailing_metadata = self.metadata_to_dict(error.trailing_metadata())
            text = status_details
            self._finish_call_trace(call_step, {
                'grpc_status_code': status_code,
                'grpc_status_details': status_details,
                'trailing_metadata_keys': list(trailing_metadata.keys()),
            })
        except AutoApiError as error:
            self._fail_call_trace(call_step, error.msg)
            raise
        except Exception as error:
            self._fail_call_trace(call_step, str(error))
            log.api.error(f'gRPC调用异常，错误数据：{request_data.model_dump_json()}，报错内容：{error}')
            raise AutoApiError(GRPC_API_FAILED, value=(str(error),)) from error
        finally:
            if self.channel_manager is None and channel is not None:
                try:
                    channel.close()
                except Exception:
                    pass

        return ApiExecutionResponse(
            code=None,
            time=time.time() - start_time,
            url=request_data.url,
            response_mode=ApiProtocolTypeEnum.GRPC.value,
            request_protocol_type=request_data.protocol_type,
            request_body_type=request_data.body_type,
            request_headers=dict(metadata),
            request_params=request_data.params,
            request_json=arguments,
            request_body=arguments,
            request_content_type='application/grpc',
            headers={**initial_metadata, **trailing_metadata},
            json=response_json,
            text=text,
            grpc_service_id=request_data.grpc_service_id,
            grpc_method_id=request_data.grpc_method_id,
            grpc_full_method=request_data.grpc_full_method,
            grpc_request_message=request_data.grpc_request_message,
            grpc_response_message=request_data.grpc_response_message,
            grpc_status_code=status_code,
            grpc_status_details=status_details,
            grpc_initial_metadata=initial_metadata,
            grpc_trailing_metadata=trailing_metadata,
        )

    @classmethod
    def business_metadata(cls, headers: dict | None) -> list[tuple[str, str]]:
        metadata = []
        for key, value in (headers or {}).items():
            key_text = str(key).lower()
            if key_text in cls.RESERVED_METADATA:
                continue
            metadata.append((key_text, str(value)))
        return metadata

    @staticmethod
    def message_to_dict(message, include_default_values: bool) -> dict:
        kwargs = {'preserving_proto_field_name': True}
        if include_default_values:
            try:
                return json_format.MessageToDict(
                    message,
                    **kwargs,
                    always_print_fields_with_no_presence=True,
                )
            except TypeError:
                return json_format.MessageToDict(
                    message,
                    **kwargs,
                    including_default_value_fields=True,
                )
        return json_format.MessageToDict(message, **kwargs)

    @staticmethod
    def validate_json_schema(value: Any, schema: dict | None, name: str):
        if not isinstance(schema, dict) or not schema:
            return
        try:
            jsonschema.validate(instance=value, schema=schema)
        except jsonschema.ValidationError as error:
            path = '.'.join(str(item) for item in error.absolute_path)
            prefix = f'{name}字段【{path}】' if path else name
            raise AutoApiError(AUTO_API_PROTOCOLS_GRPC_JSON_INVALID, value=(prefix, error.message)) from error
        except jsonschema.SchemaError as error:
            raise AutoApiError(AUTO_API_PROTOCOLS_GRPC_JSON_INVALID_CODE_JSON_INVALID,
                               value=(name, error.message)) from error

    @staticmethod
    def metadata_to_dict(metadata) -> dict:
        result = {}
        for item in metadata or []:
            try:
                key, value = item
            except Exception:
                continue
            result[str(key)] = value.decode() if isinstance(value, bytes) else value
        return result

    @staticmethod
    def target_from_config(grpc_config: dict, url: str | None) -> str:
        target = grpc_config.get('target') or grpc_config.get('grpc_target')
        if target:
            return str(target).strip()
        return GrpcProtocolClient.target_from_url(url)

    @staticmethod
    def target_from_url(url: str | None) -> str:
        value = str(url or '')
        parsed = urlparse(value)
        if parsed.scheme and parsed.netloc:
            return parsed.netloc
        if value.startswith('http://'):
            return value[len('http://'):]
        if value.startswith('https://'):
            return value[len('https://'):]
        return value

    @staticmethod
    def create_channel(target: str, grpc_config: dict, headers: dict | None):
        options = []
        if grpc_config.get('authority'):
            options.append(('grpc.default_authority', str(grpc_config.get('authority'))))
        if grpc_config.get('tls_enabled'):
            root_certificates = None
            root_certificates_text = grpc_config.get('root_certificates')
            if root_certificates_text:
                root_certificates = str(root_certificates_text).encode('utf-8')
            credentials = grpc.ssl_channel_credentials(root_certificates=root_certificates)
            return grpc.secure_channel(target, credentials, options=options)
        return grpc.insecure_channel(target, options=options)

    def _get_channel(self, target: str, grpc_config: dict):
        if self.channel_manager is not None:
            return self.channel_manager.get_channel(target, grpc_config)
        return self.create_channel(target, grpc_config, None)

    def _start_call_trace(self, request_data: ApiExecutionRequest, target: str, timeout: int,
                          metadata: list[tuple[str, str]]):
        manager = self.channel_manager
        if manager is None or not manager.trace_recorder:
            return None
        return manager.trace_recorder.start_step(
            ApiCaseTraceStepType.GRPC_CALL,
            f'gRPC调用：{request_data.grpc_full_method}',
            {
                'target': target,
                'full_method': request_data.grpc_full_method,
                'request_message': request_data.grpc_request_message,
                'response_message': request_data.grpc_response_message,
                'timeout_seconds': timeout,
                'metadata_fingerprint': manager.metadata_fingerprint(dict(metadata)),
                'request_keys': list((request_data.request_body or {}).keys()) if isinstance(request_data.request_body,
                                                                                             dict) else None,
            },
            parent_step_id=request_data.trace_parent_step_id,
        )

    def _finish_call_trace(self, step, output_summary: dict):
        manager = self.channel_manager
        if manager is not None and manager.trace_recorder:
            manager.trace_recorder.finish_step(step, output_summary)

    def _fail_call_trace(self, step, error_message: str):
        manager = self.channel_manager
        if manager is not None and manager.trace_recorder:
            manager.trace_recorder.fail_step(step, error_message)


class GrpcChannelManager:
    """单次 API Case 执行内的 gRPC Channel 管理器。"""

    def __init__(self, trace_recorder=None):
        self.trace_recorder = trace_recorder
        self._channels: dict[str, Any] = {}
        self._closed = False

    def get_channel(self, target: str, grpc_config: dict):
        key = self.channel_key(target, grpc_config)
        if key in self._channels:
            step = self._start_trace_step(
                ApiCaseTraceStepType.GRPC_CHANNEL_INIT,
                '复用 gRPC Channel',
                {
                    'target': target,
                    'tls_enabled': bool(grpc_config.get('tls_enabled')),
                    'reused': True,
                },
                None,
            )
            self._finish_trace_step(step, {'reused': True})
            return self._channels[key]
        step = self._start_trace_step(
            ApiCaseTraceStepType.GRPC_CHANNEL_INIT,
            '初始化 gRPC Channel',
            {
                'target': target,
                'tls_enabled': bool(grpc_config.get('tls_enabled')),
                'authority': grpc_config.get('authority'),
                'reused': False,
            },
            None,
        )
        try:
            channel = GrpcProtocolClient.create_channel(target, grpc_config, None)
            self._channels[key] = channel
            self._finish_trace_step(step, {'reused': False})
            return channel
        except Exception as error:
            self._fail_trace_step(step, str(error))
            raise

    def close(self):
        if self._closed:
            return
        self._closed = True
        step = self._start_trace_step(
            ApiCaseTraceStepType.GRPC_CHANNEL_CLOSE,
            '关闭 gRPC Channel',
            {'channel_count': len(self._channels)},
            None,
        )
        try:
            channels = list(self._channels.values())
            self._channels = {}
            for channel in channels:
                try:
                    channel.close()
                except Exception as error:
                    log.api.error(f'gRPC Channel关闭单个连接失败：{error}')
            self._finish_trace_step(step)
        except Exception as error:
            self._fail_trace_step(step, str(error))
            log.api.error(f'gRPC Channel关闭失败：{error}')

    @staticmethod
    def channel_key(target: str, grpc_config: dict) -> str:
        payload = json.dumps(
            {
                'target': target,
                'tls_enabled': bool(grpc_config.get('tls_enabled')),
                'authority': grpc_config.get('authority'),
                'root_certificates': grpc_config.get('root_certificates') or '',
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(',', ':'),
        )
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    @staticmethod
    def metadata_fingerprint(metadata: dict) -> str:
        payload = json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]

    def _start_trace_step(self, step_type: str, step_name: str, input_summary: Any, parent_step_id: int | None):
        if not self.trace_recorder:
            return None
        return self.trace_recorder.start_step(
            step_type,
            step_name,
            input_summary,
            parent_step_id=parent_step_id,
        )

    def _finish_trace_step(self, step, output_summary: Any = None):
        if self.trace_recorder:
            self.trace_recorder.finish_step(step, output_summary)

    def _fail_trace_step(self, step, error_message: str | None):
        if self.trace_recorder:
            self.trace_recorder.fail_step(step, error_message)
