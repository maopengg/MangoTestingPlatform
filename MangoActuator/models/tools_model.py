# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-11-20 14:19
# @Author : 毛鹏
from pydantic import BaseModel


class MysqlConingModel(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str | None
