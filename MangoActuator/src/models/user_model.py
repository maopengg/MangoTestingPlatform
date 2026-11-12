# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-09-21 11:23
# @Author : 毛鹏
from datetime import datetime

from mangotools.decorator import singleton
from pydantic import BaseModel


class UserConfigModel(BaseModel):
    pass


@singleton
class ActuatorUserProfile(BaseModel):
    """用户表"""
    id: int
    create_time: datetime
    update_time: datetime
    name: str
    username: str
    role: int | dict | None = None
    ip: str | None = None
    selected_project: int | None = None
    selected_environment: int | None = None
    config: UserConfigModel | None = None

    def update(self, **kwargs):
        """更新用户信息"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
