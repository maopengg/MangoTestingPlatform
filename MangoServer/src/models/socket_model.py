# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-21 21:28
# @Author : 毛鹏
from typing import Union, Optional, TypeVar

from pydantic import BaseModel

from src.enums.system_enum import ClientTypeEnum

T = TypeVar('T')


class QueueModel(BaseModel):
    func_name: str
    func_args: Optional[Union[list[T], T]]


class SocketDataModel(BaseModel):
    code: int
    msg: str
    user: str | None = None
    is_notice: ClientTypeEnum | None = None
    data: QueueModel | None = None
