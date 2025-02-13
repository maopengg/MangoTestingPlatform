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
    tasks_id: int | None = None


class RequestModel(BaseModel):
    method: str | None
    url: str | None
    headers: dict | None = None
    params: dict | list | str | None = None
    data: dict | list | None = None
    json: dict | list | None = None
    file: list[dict] | Any | None = None

class ResponseModel(BaseModel):
    code: int
    time: float
    headers: dict
    json: dict | None = None
    text: str | None = None


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
    json: list | dict | None = None
    file: str | None = None
    status: int | None = None


class AssResultModel(BaseModel):
    type: str
    expect: str | None
    actual: str | None


class ApiCaseStepsResultModel(BaseModel):
    """接口结果"""
    id: int
    api_info_id: int
    name: str
    status: int
    error_message: str | None = None
    ass: list[AssResultModel]
    request: RequestModel
    response: ResponseModel
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
