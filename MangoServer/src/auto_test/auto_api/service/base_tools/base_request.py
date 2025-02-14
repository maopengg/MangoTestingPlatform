# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-25 20:10
# @Author : 毛鹏

import time
from requests import Response
from requests.exceptions import *

from mangokit import requests
from src.auto_test.auto_system.service.cache_data_value import CacheDataValue
from src.enums.system_enum import CacheDataKeyEnum
from src.exceptions import *
from src.models.api_model import RequestModel, ResponseModel


class BaseRequest:

    def __init__(self):
        self.timeout = CacheDataValue.get_cache_value(CacheDataKeyEnum.API_TIMEOUT.name)

    def http(self, request_data: RequestModel) -> ResponseModel:
        try:
            log.api.debug(f'开始执行接口：{request_data.model_dump_json()}')
            s = time.time()
            response = requests.request(
                method=request_data.method,
                url=request_data.url,
                headers=request_data.headers,
                params=request_data.params,
                data=request_data.data,
                json=request_data.json,
                files=request_data.file,
                timeout=int(self.timeout)
            )
        except ProxyError:
            raise ApiError(*ERROR_MSG_0001)
        except SSLError:
            raise ApiError(*ERROR_MSG_0001)
        except Timeout:
            raise ApiError(*ERROR_MSG_0037)
        except RequestException as error:
            log.api.error(f'接口请求时发生未知错误，错误数据：{request_data.dict()}，报错内容：{error}')
            raise ApiError(*ERROR_MSG_0002)
        response_json = None
        if 'application/json' in response.headers.get('Content-Type', ''):
            response_json = response.json()
        response = ResponseModel(
            code=response.status_code,
            time=time.time() - s,
            headers=response.headers,
            json=response_json,
            text=response.text
        )

        log.api.debug(f'API响应数据：{response.model_dump_json()}')
        return response

    @classmethod
    def test_http(cls, request_data: RequestModel) -> Response:
        s = time.time()
        response = requests.request(
            method=request_data.method,
            url=request_data.url,
            headers=request_data.headers,
            params=request_data.params,
            data=request_data.data,
            json=request_data.json,
            files=request_data.file,
            timeout=int(30)
        )
        end = time.time() - s
        return response

#
# class BaseRequest:
#
#     def __init__(self):
#         self.timeout = CacheDataValue.get_cache_value(CacheDataKeyEnum.API_TIMEOUT.name)
#
#     async def http(self, request_data: RequestModel) -> ResponseModel:
#         async_requests.timeout = int(self.timeout)
#         return await async_requests.request(
#             method=request_data.method,
#             url=request_data.url,
#             headers=request_data.headers,
#             params=request_data.params,
#             data=request_data.data,
#             json=request_data.json_data,
#         )
#
#     @classmethod
#     async def test_http(cls, request_data: RequestModel) -> ResponseModel:
#         response = await async_requests.request(
#             method=request_data.method,
#             url=request_data.url,
#             headers=request_data.headers,
#             params=request_data.params,
#             data=request_data.data,
#             json=request_data.json_data,
#             files=request_data.file,
#             timeout=int(30)
#         )
#         return response
