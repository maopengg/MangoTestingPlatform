# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-23 20:28
# @Author : 毛鹏
import asyncio

from PyAutoTest.models.api_model import ApiCaseModel


class TestCase:

    def __init__(self, api_case_model: ApiCaseModel):
        print(api_case_model.model_dump_json())

    async def case_main(self):
        await asyncio.sleep(5)
        print(id(self))

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
