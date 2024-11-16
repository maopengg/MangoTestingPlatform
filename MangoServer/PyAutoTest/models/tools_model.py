# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
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


class WeChatNoticeModel(BaseModel):
    webhook: str


class EmailNoticeModel(BaseModel):
    send_user: str
    email_host: str
    stamp_key: str
    send_list: list
