# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/5/10 11:43
# @Author : 毛鹏
import asyncio

from auto_ui.test_runner.debug_case_run import CaseDistribution
from auto_ui.test_runner.group_case_run import GroupCaseRun


class ConsumeUI:
    semaphore = asyncio.Semaphore(10)

    @staticmethod
    async def debug_case(data: dict):
        await CaseDistribution().debug_case_distribution(data)

    @classmethod
    async def group_case(cls, data: dict):
        async def run():
            await GroupCaseRun().group_obj(data)

        async with cls.semaphore:
            asyncio.create_task(run())
