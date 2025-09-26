# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-07-04 17:14
# @Author : 毛鹏
from datetime import datetime

from pydantic import BaseModel


class FileModel(BaseModel):
    name: str
    path: str
    time: datetime


class UpdateFileModel(BaseModel):
    project_name: str
    auto_test: list[FileModel] | list = []
    init_file_path: str
    module_name: list[str] | list


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
    git_url: str
    commit_hash: str
    git_username: str | None = None
    git_password: str | None = None


class PytestCaseResultModel(BaseModel):
    id: int
    name: str
    status: int
    result_data: dict | list | None = None
