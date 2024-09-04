# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏

import aiohttp
from aiohttp.client_exceptions import ClientResponse

from src.models.api_model import RequestModel
from src.services.api.service.case_run import ApiCaseRun
from src.tools.decorator.convert_args import convert_args


class APIConsumer:
    api = ApiCaseRun()

    @classmethod
    @convert_args(RequestModel)
    async def a_api_info(cls, data: RequestModel):
        response: ClientResponse | None = None
        time = None
        session = aiohttp.ClientSession()
        response, time = await cls.api.http_(session, data)
        await session.close()

    @classmethod
    @convert_args(RequestModel)
    async def a_api_case(cls, data: RequestModel):
        pass
