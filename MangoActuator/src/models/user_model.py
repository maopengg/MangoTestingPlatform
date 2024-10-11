# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-21 11:23
# @Author : 毛鹏
from datetime import datetime
from mangokit import singleton
from pydantic import BaseModel



class UserConfigModel(BaseModel):
    web_max: bool = False
    web_recording: bool = False
    web_parallel: int = 10
    web_type: int = 0
    web_h5: str | None = None
    web_path: str | None = None
    web_headers: bool = False
    and_equipment: str | None = None


@singleton
class UserModel(BaseModel):
    """用户表"""
    id: int
    create_time: datetime
    update_time: datetime
    nickname: str
    username: str
    role: int | dict | None = None
    ip: str | None = None
    mailbox: list[str] | None = None
    selected_project: int | None = None
    selected_environment: int | None = None
    last_login_time: datetime | None = None
    config: UserConfigModel

    def update(self, **kwargs):
        """更新用户信息"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
