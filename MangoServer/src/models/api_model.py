# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2022-12-04 17:14
# @Author : 毛鹏
import json
import warnings
from typing import Any

from pydantic import BaseModel

from src.exceptions import ApiError, ERROR_MSG_0003
from src.tools.log_collector import log

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
    params: str | None = None
    data: str | None = None
    json: str | None = None
    file: list[dict] | Any | None = None
    posterior_file: str | None = None

    def serialize(self):
        for field in ['data', 'json', 'params']:
            field_value = getattr(self, field)
            if field_value is not None:
                try:
                    parsed = json.loads(field_value, strict=False)
                    if not isinstance(parsed, (dict, list)):
                        log.api.info(f'序列化失败-1：{parsed}')
                        raise ApiError(*ERROR_MSG_0003, value=(_a.get(field),))
                    setattr(self, field, parsed)
                except json.JSONDecodeError:
                    log.api.info(f'序列化失败-2：{field_value}')
                    raise ApiError(*ERROR_MSG_0003, value=(_a.get(field),))


class ResponseModel(BaseModel):
    code: int
    time: float
    request_headers: dict | None = None
    request_params: dict | list | str | None = None
    request_data: dict | list | None = None
    request_json: dict | list | None = None
    request_file: list[dict] | Any | None = None
    headers: dict
    json: dict | list | None = None
    text: str | None = None


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
    params: list | dict | None = None
    data: list | dict | None = None
    json: list | dict | None = None
    file: str | None = None
    status: int | None = None


class AssResultModel(BaseModel):
    method: str
    expect: str | None = None
    actual: Any | None
    ass_msg: str | None = None


class ApiCaseStepsResultModel(BaseModel):
    """接口结果"""
    id: int
    name: str
    status: int
    error_message: str | None = None
    test_time: str | None = None
    api_info_id: int
    ass: list[AssResultModel] | None = None
    request: RequestModel
    response: ResponseModel | None = None
    cache_data: dict


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
