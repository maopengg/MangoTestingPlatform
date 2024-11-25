# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-25 20:10
# @Author : 毛鹏
import time

from PyAutoTest.auto_test.auto_system.service.cache_data_value import CacheDataValue
from PyAutoTest.enums.system_enum import CacheDataKeyEnum
from PyAutoTest.models.api_model import RequestDataModel
from mangokit import async_requests, ResponseModel


class BaseRequest:

    def __init__(self):
        self.timeout = CacheDataValue.get_cache_value(CacheDataKeyEnum.API_TIMEOUT.name)

    async def http(self, request_data: RequestDataModel) -> ResponseModel:
        async_requests.timeout = int(self.timeout)
        return await async_requests.request(
            method=request_data.method,
            url=request_data.url,
            headers=request_data.headers,
            params=request_data.params,
            data=request_data.data,
            json=request_data.json_data,
        )

    @classmethod
    async def test_http(cls, request_data: RequestDataModel) -> ResponseModel:
        response = await async_requests.request(
            method=request_data.method,
            url=request_data.url,
            headers=request_data.headers,
            params=request_data.params,
            data=request_data.data,
            json=request_data.json_data,
            files=request_data.file,
            timeout=int(30)
        )
        return response
