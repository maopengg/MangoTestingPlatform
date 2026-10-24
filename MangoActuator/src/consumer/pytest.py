# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2025-08-27 11:21
# @Author : 毛鹏
from mangotools.contracts import PytestExecutionCommand
from src.services.pytest.test_case import TestCase
from src.tools.decorator import convert_args


class Pytest:

    @classmethod
    @convert_args(PytestExecutionCommand)
    async def p_case(cls, data: PytestExecutionCommand):
        async with TestCase(None, data, report_result=False) as test_case:
            await test_case.test_case()
            return test_case.case_result
