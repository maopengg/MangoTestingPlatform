# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-17 15:00
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
