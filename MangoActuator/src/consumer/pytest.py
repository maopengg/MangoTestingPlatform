# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-08-27 11:21
# @Author : 毛鹏
from src.models.pytest_model import PytestCaseModel
from src.services.pytest.case_flow import PytestCaseFlow
from src.tools.decorator import convert_args


class Pytest:

    @classmethod
    @convert_args(PytestCaseModel)
    async def p_case(cls, data: PytestCaseModel):
        await PytestCaseFlow.add_task(data)
