# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2022-12-04 17:14
# @Author : 毛鹏
import json
import warnings
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.common.enums.api_enum import ApiBodyTypeEnum, ApiProtocolTypeEnum
from src.common.enums.tools_enum import StatusEnum
from src.common.exceptions import ApiError, ERROR_MSG_0003, ERROR_MSG_0078, ERROR_MSG_0079
from src.common.tools.log_collector import log

warnings.filterwarnings("ignore", category=UserWarning)

_a = {
    'data': '表单',
    'json': 'json',
    'params': '参数',
}


class RequestModel(BaseModel):
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

    @field_validator('protocol_type')
    @classmethod
    def validate_protocol_type(cls, value):
        value = value or ApiProtocolTypeEnum.HTTP.value
        if value not in ApiProtocolTypeEnum.obj():
            raise ApiError(*ERROR_MSG_0078, value=(value,))
        return value

    @field_validator('body_type')
    @classmethod
    def validate_body_type(cls, value):
        value = value or ApiBodyTypeEnum.NONE.value
        if value not in ApiBodyTypeEnum.obj():
            raise ApiError(*ERROR_MSG_0079, value=(value, '不支持的请求体类型'))
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
                    raise ApiError(*ERROR_MSG_0003, value=(_a.get(field),))


class ResponseModel(BaseModel):
    code: int
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
    error_msg: str | None = None


class RecordingApiModel(BaseModel):
    """ApiInfo模型"""
    project_product: int
    username: str
    type: int = 0
    module: int | None = None
    name: str
    client: int = 0
    url: str
    method: int
    header: dict | None = None
    params: str | None = None
    protocol_type: str = ApiProtocolTypeEnum.HTTP.value
    body_type: str = ApiBodyTypeEnum.NONE.value
    body_config: dict | None = None
    sse_config: dict | None = None
    status: int | None = None


class AssResultModel(BaseModel):
    method: str
    expect: Any | None = None
    actual: Any | None = None
    ass_msg: str | None = None
    status: int = StatusEnum.SUCCESS.value


class ApiCaseStepsResultModel(BaseModel):
    """接口结果"""
    id: int
    name: str
    status: int
    error_message: str | None = None
    test_time: str | None = None
    api_info_id: int
    api_info_name: str
    ass: list[AssResultModel] | None = None
    request: RequestModel
    response: ResponseModel | None = None
    cache_data: dict
    data_factory_cache_data: dict = Field(default_factory=dict)


class ApiCaseResultModel(BaseModel):
    """用例结果"""
    id: int
    name: str
    project_product_name: str
    status: int
    error_message: str | None = None
    test_time: str | None = None
    test_env: int
    user_id: int
    steps: list[ApiCaseStepsResultModel] = []
