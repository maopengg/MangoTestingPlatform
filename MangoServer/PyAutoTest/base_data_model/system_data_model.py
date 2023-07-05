# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-07-04 13:25
# @Author : 毛鹏
from typing import Dict,Union

from pydantic import BaseModel

from PyAutoTest.base_data_model.ui_data_model import CaseGroupModel
from PyAutoTest.enums.system_enum import ClientTypeEnum


class QueueModel(BaseModel):
    func_name: str
    func_args: None | list[CaseGroupModel] | CaseGroupModel


class SocketDataModel(BaseModel):
    code: int
    msg: str
    user: str = None
    is_notice: ClientTypeEnum | None = None
    data: QueueModel | None = None
