# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-08 15:48
# @Author : 毛鹏
from pydantic import BaseModel

from PyAutoTest.models.ui_model import CaseResultModel


class TestSuiteDetailsResultModel(BaseModel):
    id: int | None = None
    test_suite: int | None = None
    status: int
    error_message: str | None = None
    result_data: CaseResultModel
