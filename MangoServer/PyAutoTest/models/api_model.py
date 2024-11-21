# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2022-12-04 17:14
# @Author : 毛鹏

from typing import Any

from pydantic import BaseModel


class RequestDataModel(BaseModel):
    method: str | None
    url: str | None
    headers: str | dict | list | None = None
    params: dict | list | str | None = None
    data: dict | list | None = None
    json_data: dict | list | None = None
    file: list[dict] | Any | None = None


class ResponseDataModel(BaseModel):
    url: str
    method: str
    headers: dict | list | None = None
    params: dict | None = None
    data: dict | None = None
    json_data: dict | list | None = None
    file: str | None = None
    status_code: int
    response_time: float
    response_headers: dict
    response_json: dict | None = None
    response_text: str


class RequestModel(BaseModel):
    """请求"""
    case_id: int
    case_name: str
    url: str
    method: str
    header: str | None
    body_type: int = None
    body: dict | str = None


class ApiCaseGroupModel(BaseModel):
    group_name: str
    case_group_list: list[RequestModel]


class PublicModel(BaseModel):
    end: int
    public_type: int
    name: str
    key: str
    value: str


class ResponseModel(BaseModel):
    case_id: int
    case_name: str
    url: str
    method: str
    header: dict
    response_time: float
    res_code: int
    body_type: int = None
    body: dict = None
    response: dict
    assertion_res: bool = None


class ApiPublicModel(BaseModel):
    """api公共"""
    project_id: int
    client: int
    public_type: int
    name: str
    key: str
    value: str
    status: int
    type: int


class ApiInfoModel(BaseModel):
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
