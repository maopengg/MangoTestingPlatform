# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2022-12-04 17:14
# @Author : 毛鹏
import json
import warnings
from typing import Any

from django.conf import settings
from mangotools.enums import StatusEnum
from pydantic import Field, field_validator, model_serializer

from src.apps.auto_api.enums import ApiBodyTypeEnum, ApiProtocolTypeEnum
from src.apps.auto_api.exceptions import (
    AutoApiError,
    API_JSON_SERIALIZATION_ERROR,
    API_PROTOCOL_UNSUPPORTED,
    API_REQUEST_BODY_INVALID,
)
from src.common.logging import log
from src.common.schemas import StrictSchema

warnings.filterwarnings("ignore", category=UserWarning)

_a = {
    'data': '表单',
    'json': 'json',
    'params': '参数',
}


def _truncate_assertion_result_value(value: Any) -> Any:
    """只压缩持久化诊断副本，不改变断言执行期间使用的原始值。"""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, default=str, separators=(',', ':'))
        except (TypeError, ValueError):
            text = str(value)
    max_length = max(1, int(getattr(settings, 'ASSERTION_RESULT_DISPLAY_MAX_LENGTH', 500) or 500))
    if len(text) <= max_length:
        return value
    suffix = f'…（已截断，共{len(text)}字符）'
    if len(suffix) >= max_length:
        return text[:max_length]
    return f'{text[:max_length - len(suffix)]}{suffix}'


class ApiExecutionRequest(StrictSchema):
    method: str | None
    url: str | None
    headers: dict | None = None
    params: dict | list | str | None = None
    protocol_type: str = ApiProtocolTypeEnum.HTTP.value
    body_type: str = ApiBodyTypeEnum.NONE.value
    body_config: dict | None = None
    sse_config: dict | None = None
    posterior_file: str | None = None

    request_body: Any | None = None
    request_files: list[dict] | None = None
    request_content_type: str | None = None
    mcp_server_id: int | None = None
    mcp_tool_id: int | None = None
    mcp_tool_name: str | None = None
    mcp_config: dict | None = None
    grpc_service_id: int | None = None
    grpc_method_id: int | None = None
    grpc_full_method: str | None = None
    grpc_request_message: str | None = None
    grpc_response_message: str | None = None
    grpc_config: dict | None = None
    trace_parent_step_id: int | None = None

    @property
    def json(self):
        if self.body_type != ApiBodyTypeEnum.JSON.value:
            return None
        body_config = self.body_config or {}
        if body_config.get('source_type') == 'template':
            return body_config.get('body_text')
        return body_config.get('body')

    @json.setter
    def json(self, value):
        if value is None:
            if self.body_type == ApiBodyTypeEnum.JSON.value:
                self.body_type = ApiBodyTypeEnum.NONE.value
                self.body_config = None
            return
        self.body_type = ApiBodyTypeEnum.JSON.value
        if isinstance(value, str):
            self.body_config = {'source_type': 'template', 'body_text': value}
        else:
            self.body_config = {'source_type': 'value', 'body': value}

    @property
    def data(self):
        body_config = self.body_config or {}
        if self.body_type == ApiBodyTypeEnum.FORM.value:
            fields = body_config.get('fields') or []
            if isinstance(fields, list):
                return {item.get('key'): item.get('value') for item in fields if isinstance(item, dict)}
            return fields
        if self.body_type == ApiBodyTypeEnum.RAW.value:
            return body_config.get('body_text')
        if self.body_type == ApiBodyTypeEnum.MULTIPART.value:
            fields = body_config.get('fields') or []
            return {item.get('key'): item.get('value') for item in fields if isinstance(item, dict)}
        return None

    @data.setter
    def data(self, value):
        if value is None:
            if self.body_type in {ApiBodyTypeEnum.FORM.value, ApiBodyTypeEnum.RAW.value}:
                self.body_type = ApiBodyTypeEnum.NONE.value
                self.body_config = None
            return
        if isinstance(value, dict):
            fields = [{'key': key, 'value': item} for key, item in value.items()]
            self.body_type = ApiBodyTypeEnum.FORM.value
            self.body_config = {'fields': fields}
        elif isinstance(value, list):
            self.body_type = ApiBodyTypeEnum.FORM.value
            self.body_config = {'fields': value}
        else:
            self.body_type = ApiBodyTypeEnum.RAW.value
            self.body_config = {'body_text': value, 'content_type': 'application/json'}

    @property
    def file(self):
        if self.body_type != ApiBodyTypeEnum.MULTIPART.value:
            return None
        return (self.body_config or {}).get('files')

    @file.setter
    def file(self, value):
        if value in [None, '', [], {}]:
            if self.body_type == ApiBodyTypeEnum.MULTIPART.value:
                fields = (self.body_config or {}).get('fields') or []
                if fields:
                    self.body_config = {'fields': fields, 'files': []}
                else:
                    self.body_type = ApiBodyTypeEnum.NONE.value
                    self.body_config = None
            return
        body_config = self.body_config or {}
        self.body_type = ApiBodyTypeEnum.MULTIPART.value
        self.body_config = {
            'fields': body_config.get('fields') or [],
            'files': value if isinstance(value, list) else [value],
        }

    @field_validator('protocol_type')
    @classmethod
    def validate_protocol_type(cls, value):
        value = value or ApiProtocolTypeEnum.HTTP.value
        if value not in ApiProtocolTypeEnum.obj():
            raise AutoApiError(API_PROTOCOL_UNSUPPORTED, value=(value,))
        return value

    @field_validator('body_type')
    @classmethod
    def validate_body_type(cls, value):
        value = value or ApiBodyTypeEnum.NONE.value
        if value not in ApiBodyTypeEnum.obj():
            raise AutoApiError(API_REQUEST_BODY_INVALID, value=(value, '不支持的请求体类型'))
        return value

    def serialize(self):
        for field in ['params']:
            field_value = getattr(self, field)
            if field_value is not None:
                if isinstance(field_value, (dict, list)):
                    continue
                try:
                    parsed = json.loads(field_value, strict=False)
                    setattr(self, field, parsed if isinstance(parsed, (dict, list)) else field_value)
                except json.JSONDecodeError:
                    if field == 'params' and not field_value.lstrip().startswith(('{', '[')):
                        continue
                    log.api.info(f'序列化失败-2：{field_value}')
                    raise AutoApiError(API_JSON_SERIALIZATION_ERROR, value=(_a.get(field),))


class ApiExecutionResponse(StrictSchema):
    code: int | None
    time: float
    url: str | None = None
    response_mode: str = ApiProtocolTypeEnum.HTTP.value
    request_protocol_type: str | None = None
    request_body_type: str | None = None
    request_headers: dict | None = None
    request_params: dict | list | str | None = None
    request_data: Any | None = None
    request_json: Any | None = None
    request_file: list[dict] | Any | None = None
    request_body: Any | None = None
    request_content_type: str | None = None
    headers: dict
    json: Any | None = None
    text: str | None = None
    sse_events: list[dict] | None = None
    sse_stop_reason: str | None = None
    mcp_server_id: int | None = None
    mcp_tool_id: int | None = None
    mcp_tool_name: str | None = None
    mcp_protocol_version: str | None = None
    mcp_content: list[dict] | None = None
    mcp_structured_content: dict | list | str | int | float | bool | None = None
    mcp_is_error: bool | None = None
    mcp_meta: dict | None = None
    mcp_notifications: list[dict] | None = None
    mcp_task: dict | None = None
    mcp_protocol_error: dict | None = None
    grpc_service_id: int | None = None
    grpc_method_id: int | None = None
    grpc_full_method: str | None = None
    grpc_request_message: str | None = None
    grpc_response_message: str | None = None
    grpc_status_code: str | None = None
    grpc_status_details: str | None = None
    grpc_initial_metadata: dict | None = None
    grpc_trailing_metadata: dict | None = None
    ws_messages: list[dict] | None = None
    ws_close_code: int | None = None
    ws_close_reason: str | None = None
    ws_stop_reason: str | None = None
    error_msg: str | None = None
    api_info_posterior_skipped_reason: str | None = None

    @model_serializer(mode='wrap')
    def serialize_response(self, handler):
        """运行时保留原始文本；持久化时避免重复保存可由 JSON 完整表达的响应。"""
        data = handler(self)
        if self.json is not None and self.response_mode != ApiProtocolTypeEnum.SSE.value:
            data.pop('text', None)
        return data


class ApiCallbackAssertionContext(StrictSchema):
    run_id: int
    rule_key: str
    run_status: str | None = None
    events: int | None = None
    deliveries: int | None = None
    delivery_id: int | None = None
    event_id: str | None = None
    received_at: str | None = None
    check_key: str | None = None
    check_type: str | None = None
    source: str | None = None
    field: str | None = None
    diagnostic: bool = False
    passed: bool | None = None
    assertions: list[dict[str, Any]] = Field(default_factory=list)


class ApiAssertionResult(StrictSchema):
    method: str
    expect: Any | None = None
    actual: Any | None = None
    ass_msg: str | None = None
    status: int = StatusEnum.SUCCESS.value
    group_name: str | None = None
    group_logic: str | None = None
    group_result: bool | None = None
    source_type: str | None = None
    assertion_index: int | None = None
    group_source_type: str | None = None
    actual_source: Any | None = None
    expect_source: Any | None = None
    raw_config: Any | None = None
    resolved_config: Any | None = None
    callback: ApiCallbackAssertionContext | None = None

    @model_serializer(mode='wrap')
    def serialize_assertion_result(self, handler):
        data = handler(self)
        data['actual'] = _truncate_assertion_result_value(data.get('actual'))
        data['ass_msg'] = _truncate_assertion_result_value(data.get('ass_msg'))
        if self.callback is None:
            data.pop('callback', None)
        else:
            data['callback'] = self.callback.model_dump(mode='json', exclude_none=True, exclude_defaults=True)
        return data


class ApiStepExecutionContext(StrictSchema):
    context_id: str
    snapshot_id: str
    parent_snapshot_id: str | None = None
    case_id: int
    case_detailed_id: int
    case_sort: int | None = None
    test_env: int
    user_id: int | None = None
    trace_id: str | None = None
    executed_at: str


class ApiCaseStepResult(StrictSchema):
    """接口结果"""
    id: int
    is_recovery: bool = False
    main_status: int | None = None
    recovery_status: int | None = None
    recovery_errors: list[str] = Field(default_factory=list)
    parameter_id: int | None = None
    retry_index: int | None = None
    automatic_retry_condition: str | None = None
    name: str
    status: int
    error_message: str | None = None
    failure_category: str | None = None
    protocol_status: str | None = None
    posterior_skipped_reason: str | None = None
    assertion_skipped_reason: str | None = None
    test_time: str | None = None
    api_info_id: int
    api_info_name: str
    ass: list[ApiAssertionResult] | None = None
    request: ApiExecutionRequest
    response: ApiExecutionResponse | None = None
    cache_data: dict
    data_factory_cache_data: dict = Field(default_factory=dict)
    execution_context: ApiStepExecutionContext | None = None


class ApiCaseExecutionResult(StrictSchema):
    """用例结果"""
    id: int
    main_status: int | None = None
    recovery_status: int | None = None
    recovery_errors: list[str] = Field(default_factory=list)
    # 仅保留运行／投递摘要；最终回调断言明细归属于触发步骤的 ass。
    callback_results: list[dict[str, Any]] = Field(default_factory=list)
    name: str
    project_product_name: str
    status: int
    error_message: str | None = None
    test_time: str | None = None
    test_env: int
    user_id: int
    trace_id: str | None = None
    execution_context_id: str | None = None
    case_revision_id: int | None = None
    case_revision_no: int | None = None
    case_release_id: int | None = None
    version_label: str | None = None
    config_checksum: str | None = None
    steps: list[ApiCaseStepResult] = []
