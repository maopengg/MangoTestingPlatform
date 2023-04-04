# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2022-12-04 17:14
# @Author : 毛鹏
from pydantic import BaseModel


class UiPage(BaseModel):
    id: int
    project: str
    url: str


class Host(BaseModel):
    url: str
    host: str | None = None


class CaseData(BaseModel):
    ope_type: list = None
    # # 用例的执行顺序文字版
    run: str = None
    # 用例的执行顺序
    run_flow: list = None
