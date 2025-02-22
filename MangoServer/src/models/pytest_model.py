# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description:
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
