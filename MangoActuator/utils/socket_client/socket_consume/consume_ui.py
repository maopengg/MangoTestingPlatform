# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/5/10 11:43
# @Author : 毛鹏
import asyncio

from auto_ui.test_runner.debug_case_run import CaseDistribution
from auto_ui.test_runner.group_case_run import GroupCaseRun
from auto_ui.ui_tools.base_model import CaseGroupModel


class ConsumeUI:
    semaphore = asyncio.Semaphore(10)

    @staticmethod
    async def debug_case(data: dict):
        await CaseDistribution().debug_case_distribution(data)

    @classmethod
    async def group_case(cls, data: dict):
        async def run():
            await GroupCaseRun().group_obj(case_group_obj)

        case_group_obj = CaseGroupModel(group_name=data['group_name'], case_group=data['case_group'])
        async with cls.semaphore:
            asyncio.create_task(run())
