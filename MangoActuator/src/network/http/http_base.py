# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-12 18:09
# @Author : 毛鹏
from urllib.parse import urljoin

import httpx

from src.enums.system_enum import ClientTypeEnum
from src.models.socket_model import ResponseModel
from src.tools.decorator.request_log import request_log
from src.tools.set_config import SetConfig


class HttpBase:
    headers = {
        'Authorization': '',
        'Source-Type': str(ClientTypeEnum.ACTUATOR.value),

    }

    @classmethod
    @request_log()
    async def get(cls, url, headers=None, **kwargs) -> ResponseModel | httpx.Response:
        async with httpx.AsyncClient() as client:
            return await client.get(urljoin(SetConfig.get_host(), url),  # type: ignore
                                headers=headers if headers else cls.headers,
                                **kwargs)

    @classmethod
    @request_log()
    async def post(cls, url, headers=None, **kwargs) -> ResponseModel | httpx.Response:
        async with httpx.AsyncClient() as client:
            return await client.post(urljoin(SetConfig.get_host(), url),  # type: ignore
                                 headers=headers if headers else cls.headers,
                                 **kwargs)

    @classmethod
    @request_log()
    async def put(cls, url, headers=None, **kwargs) -> ResponseModel | httpx.Response:
        async with httpx.AsyncClient() as client:
            return await client.put(urljoin(SetConfig.get_host(), url),  # type: ignore
                                headers=headers if headers else cls.headers,
                                **kwargs)

    @classmethod
    @request_log()
    async def delete(cls, url, headers=None, **kwargs) -> ResponseModel | httpx.Response:
        async with httpx.AsyncClient() as client:
            return await client.delete(urljoin(SetConfig.get_host(), url),  # type: ignore
                                   headers=headers if headers else cls.headers,
                                   **kwargs)
