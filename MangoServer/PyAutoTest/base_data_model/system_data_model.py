# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-07-04 13:25
# @Author : 毛鹏
from pydantic import BaseModel

from PyAutoTest.enums.system_enum import ClientTypeEnum


class QueueModel(BaseModel):
    func_name: str
    func_args: dict | None


class SocketDataModel(BaseModel):
    code: int
    msg: str
    user: int = None
    is_notice: ClientTypeEnum | None = None
    data: QueueModel | None = None
