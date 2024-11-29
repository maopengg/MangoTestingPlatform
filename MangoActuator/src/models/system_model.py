# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-08 15:48
# @Author : 毛鹏
from pydantic import BaseModel

from src.models.ui_model import UiCaseResultModel


class TestSuiteDetailsResultModel(BaseModel):
    id: int
    test_suite: int
    status: int
    error_message: str | None = None
    result_data: UiCaseResultModel
