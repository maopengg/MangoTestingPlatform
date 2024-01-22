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
    db: str | None


class TestReportModel(BaseModel):
    test_suite_id: int
    case_sum: int
    success: int
    success_rate: float
    warning: int
    fail: int
    execution_duration: int
    test_time: str
    ip: str
    test_environment: str
    project: str
