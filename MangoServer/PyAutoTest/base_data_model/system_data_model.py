# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-07-04 13:25
# @Author : 毛鹏

from pydantic import BaseModel

from PyAutoTest.base_data_model.ui_data_model import CaseGroupModel, CaseModel, CaseResult, GroupCaseResult
from PyAutoTest.enums.system_enum import ClientTypeEnum
from PyAutoTest.base_data_model.api_data_model import RequestModel, ApiCaseGroupModel, PublicModel


class QueueModel(BaseModel):
    func_name: str
    func_args: None | list[
        CaseGroupModel] | CaseGroupModel | CaseModel | CaseResult | GroupCaseResult | RequestModel | ApiCaseGroupModel | PublicModel


class SocketDataModel(BaseModel):
    code: int
    msg: str
    user: str = None
    is_notice: ClientTypeEnum | None = None
    data: QueueModel | None = None
