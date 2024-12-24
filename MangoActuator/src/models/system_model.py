# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-08 15:48
# @Author : 毛鹏
from pydantic import BaseModel

from src.enums.tools_enum import AutoTestTypeEnum
from src.models.ui_model import UiCaseResultModel


class TestSuiteDetailsResultModel(BaseModel):
    id: int
    type: AutoTestTypeEnum
    test_suite: int
    status: int
    error_message: str | None = None
    result_data: UiCaseResultModel


class CmdTestModel(BaseModel):
    test_suite_details: int
    test_suite_id: int
    project_product: int
    project_product_name: str
    test_env: int
    cmd: list
