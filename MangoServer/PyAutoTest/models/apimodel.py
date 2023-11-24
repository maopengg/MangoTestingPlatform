# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-11-17 15:00
# @Author : 毛鹏
from pydantic import BaseModel


class RequestDataModel(BaseModel):
    method: str | None
    url: str | None
    headers: dict | None = None
    params: dict | None = None
    data: str | dict | None = None
    json_data: dict | None = None
    file: dict | None = None


class ResponseDataModel(BaseModel):
    url: str
    status_code: int
    method: str
    headers: dict
    params: dict | None = None
    data: str | dict | None = None
    json_data: dict | None = None
    file: dict | None = None
    text: str
    response_json: dict
