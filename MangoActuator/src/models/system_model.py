# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-08 15:48
# @Author : 毛鹏
from pydantic import BaseModel

from src.enums.tools_enum import TestCaseTypeEnum
from src.models.pytest_model import PytestCaseResultModel
from src.models.ui_model import UiCaseResultModel


class TestSuiteDetailsResultModel(BaseModel):
    id: int
    type: TestCaseTypeEnum
    test_suite: int
    status: int
    error_message: str | None = None
    result_data: UiCaseResultModel | list[dict] | PytestCaseResultModel


class CmdTestModel(BaseModel):
    test_suite_details: int
    test_suite_id: int
    project_product: int
    project_product_name: str
    test_env: int
    cmd: list


class ConsumerCaseModel(BaseModel):
    test_suite_details: int
    test_suite: int
    case_id: int
    case_name: str
    test_env: int
    user_id: int
    tasks_id: int | None = None
    parametrize: list[dict] | list = []


class SetUserOpenSatusModel(BaseModel):
    username: str
    is_open: bool | None = None
    debug: bool | None = None


class GetTaskModel(BaseModel):
    type: TestCaseTypeEnum
    username: str
