# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-09-28 16:45
# @Author : 毛鹏

from typing import Union, Optional, TypeVar

from pydantic import BaseModel

from src.enums.tools_enum import ClientTypeEnum
from src.tools.decorator.singleton import singleton

T = TypeVar('T')


class QueueModel(BaseModel):
    func_name: str
    func_args: Optional[Union[list[T], T]]


class SocketDataModel(BaseModel):
    code: int
    msg: str
    user: str | None = None
    is_notice: ClientTypeEnum | None | int = None
    data: QueueModel | None = None


@singleton
class LoginModel(BaseModel):
    ip: str
    port: str
    username: str
    password: str
    user_id: int | None = None
    token: str | None = None
    nickname: str | None = None


class ResponseModel(BaseModel):
    code: int
    msg: str
    data: list[dict] | dict | None = None
    totalSize: int | None = None