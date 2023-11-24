# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-11-08 15:48
# @Author : 毛鹏

from pydantic import BaseModel

from PyAutoTest.models.socket_model.api_model import ApiPublicModel
from PyAutoTest.models.socket_model.ui_model import UiPublicModel
from PyAutoTest.models.tools_model import MysqlDBModel


class PublicDataModel(BaseModel):
    mysql: MysqlDBModel | None
    api: list[ApiPublicModel]
    ui: list[UiPublicModel]
