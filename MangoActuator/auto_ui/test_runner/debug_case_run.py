# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏

from typing import Optional

from auto_ui.test_runner.case_run_method import CaseRunMethod
from auto_ui.ui_tools.base_model import CaseModel
from utils.decorator.singleton import singleton


@singleton
class CaseDistribution:
    """
    用例分发
    """

    def __init__(self):
        self.run: Optional[CaseRunMethod] = None

    async def debug_case_distribution(self, data: CaseModel):
        """
        处理调试用例，开始用例对象，并调用分发用例方法
        @param data:
        @return:
        """
        if not self.run:
            run = CaseRunMethod()
            self.run = run
        await self.run.distribute_to_drivers(data)

    async def test_res_send(self):
        from utils.socket_client.client_socket import ClientWebSocket
        client = ClientWebSocket()
        await client.active_send()

    async def close(self):
        await self.web.page.close()
