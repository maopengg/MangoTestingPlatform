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


class TestReportModel(BaseModel):
    test_suite_id: int
    project_id: int
    project_name: str
    test_environment: str
    case_sum: int
    success: int
    success_rate: float
    warning: int
    fail: int
    execution_duration: int
    test_time: str


class WeChatNoticeModel(BaseModel):
    webhook: str


class EmailNoticeModel(BaseModel):
    send_user: str
    email_host: str
    stamp_key: str
    send_list: list
