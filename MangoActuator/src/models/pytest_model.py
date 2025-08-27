# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-05-28 18:40
# @Author : 毛鹏
from pydantic import BaseModel


class PytestCaseModel(BaseModel):
    send_user: str
    test_suite_details: int | None
    test_suite_id: int | None
    id: int
    name: str
    project_product: int
    project_product_name: str
    module_name: str
    test_env: int
    case_people: str
    file_path: str


class PytestCaseResultModel(BaseModel):
    id: int
    name: str
    status: int
    result_data: dict | list | None = None


