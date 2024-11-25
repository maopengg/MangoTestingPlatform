# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏

import aiohttp
from aiohttp.client_exceptions import ClientResponse

from src.models.api_model import RequestModel
from src.services.api.service.case_run import ApiCaseRun
from src.tools.decorator.convert_args import convert_args


class API:
    api = ApiCaseRun()

    @convert_args(RequestModel)
    async def a_api_info(self, data: RequestModel):
        response: ClientResponse | None = None
        time = None
        session = aiohttp.ClientSession()
        response, time = await self.api.http_(session, data)
        await session.close()

    @classmethod
    @convert_args(RequestModel)
    async def a_api_case(cls, data: RequestModel):
        pass
