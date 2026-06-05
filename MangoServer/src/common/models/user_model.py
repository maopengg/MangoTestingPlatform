# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-23 21:03
# @Author : 毛鹏
from pydantic import BaseModel


class UserModel(BaseModel):
    id: int
    username: str
    name: str
    exp: int
