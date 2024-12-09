# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-08 15:48
# @Author : 毛鹏

from mango_ui import CascaderModel
from pydantic import BaseModel


class BaseDictModel(BaseModel):
    project: list[CascaderModel] | None = None
    ui_option: list


class CmdModel(BaseModel):
    cmd: str
