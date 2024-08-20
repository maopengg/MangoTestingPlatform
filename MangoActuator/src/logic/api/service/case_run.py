# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: api用例执行类
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏

from aiohttp import ClientSession
from aiohttp.client_reqrep import ClientResponse

from src.logic.api.base_tools.dependence import Dependence
from src.logic.api.base_tools.http_request import HTTPRequest
from src.models.socket_model.api_model import RequestModel
from src.tools import log


class ApiCaseRun(HTTPRequest, Dependence):

    async def http_(self, session: ClientSession, request: RequestModel) -> tuple[ClientResponse, float]:
        pass

    async def get_header(self) -> str:
        header = await self.get('header')
        if header:
            return header
        log.error(f"请求头为：{header}")

    async def request_data(self, data: str) -> str:
        return await self.replace_text(data)
