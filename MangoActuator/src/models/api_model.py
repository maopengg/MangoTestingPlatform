# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2022-12-04 17:14
# @Author : 毛鹏
from typing import Any

from pydantic import BaseModel


class ApiCaseModel(BaseModel):
    test_suite_details: int
    test_suite: int
    case_id: int
    test_env: int
    user_id: int
    tasks_id: int


class RequestDataModel(BaseModel):
    method: str | None
    url: str | None
    headers: str | dict | list | None = None
    params: dict | list | str | None = None
    data: dict | list | None = None
    json_data: dict | list | None = None
    file: list[dict] | Any | None = None


class ResponseDataModel(BaseModel):
    status_code: int
    response_time: float
    response_headers: dict
    response_json: dict | None = None
    response_text: str | None = None


class RecordingApiModel(BaseModel):
    """ApiInfo模型"""
    project_product: int
    username: str
    type: int = 0
    module_name: int | None = None
    name: str
    client: int = 0
    url: str
    method: int
    header: dict | None = None
    params: list | dict | None = None
    data: list | dict | None = None
    json_data: list | dict | None = None
    file: str | None = None
    status: int | None = None


class ApiInfoModel(BaseModel):
    """ApiInfo模型"""
    project: int
    type: int = 0
    module_name: int | None = None
    name: str
    client: int = 0
    url: str
    method: int
    header: dict | None = None
    params: list | dict | None = None
    data: list | dict | None = None
    json_data: list | dict | None = None
    file: str | None = None
    status: int | None = None


class AssResultModel(BaseModel):
    type: str
    expect: str | None
    actual: str | None


class ApiCaseStepsResultModel(BaseModel):
    """接口结果"""
    id: int
    name: str
    status: int
    error_message: str | None = None
    ass: list[AssResultModel]
    request: RequestDataModel
    response: ResponseDataModel
    cache_data: dict


class ApiCaseResultModel(BaseModel):
    """用例结果"""
    id: int
    name: str
    test_env: int
    user_id: int
    status: int
    error_message: str | None = None
    steps: list[ApiCaseStepsResultModel] = []
