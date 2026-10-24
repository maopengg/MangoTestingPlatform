# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-09-28 16:45
# @Author : 毛鹏
from mangotools.decorator import singleton
from pydantic import BaseModel


@singleton
class LoginModel(BaseModel):
    ip: str
    port: str
    username: str
    password: str
    user_id: int | None = None
    token: str | None = None
    name: str | None = None


class HttpApiResponse(BaseModel):
    code: int
    msg: str
    data: list[dict] | dict | str | None = None
    totalSize: int | None = None


class FileUploadResultModel(BaseModel):
    success: bool
    path: str | None = None
    error_type: str | None = None
    error_message: str | None = None
