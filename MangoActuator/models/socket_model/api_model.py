# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2022-12-04 17:14
# @Author : 毛鹏
from pydantic import BaseModel


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
