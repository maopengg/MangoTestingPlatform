# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
from src.enums import BaseEnum


class FileStatusEnum(BaseEnum):
    """方法枚举"""
    UNBOUND = 0
    ALREADY_BOUND = 1
    DELETED = 2

    @classmethod
    def obj(cls):
        return {0: "未绑定", 1: "已绑定", 2: "已删除"}


class PytestFileTypeEnum(BaseEnum):
    ACT = 0
    TEST_CASE = 1
    UPLOAD = 2
    TOOLS = 3

    @classmethod
    def obj(cls):
        return {0: "act", 1: "test_case", 2: "upload", 3: "tools", }
