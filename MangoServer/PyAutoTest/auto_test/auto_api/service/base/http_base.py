# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 封装请求
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import logging

import requests
import time
from requests import Response
from requests.exceptions import *

from PyAutoTest.auto_test.auto_system.service.cache_data_value import CacheDataValue
from PyAutoTest.enums.system_enum import CacheDataKeyEnum
from PyAutoTest.exceptions.api_exception import AgentError, UnknownError
from PyAutoTest.models.apimodel import RequestDataModel, ResponseDataModel
from PyAutoTest.tools.view.error_msg import *

log = logging.getLogger('api')


class HTTPRequest:

    def __init__(self):
        self.timeout = CacheDataValue.get_cache_value(CacheDataKeyEnum.API_TIMEOUT.name)
        # pass

    def http(self, request_data: RequestDataModel) -> ResponseDataModel:
        s = time.time()
        try:
            response = requests.request(
                method=request_data.method,
                url=request_data.url,
                headers=request_data.headers,
                params=request_data.params,
                data=request_data.data,
                json=request_data.json_data,
                files=request_data.file,
                timeout=int(self.timeout)
            )
            end = time.time() - s
        except ProxyError:
            raise AgentError(*ERROR_MSG_0001)
        except SSLError:
            raise AgentError(*ERROR_MSG_0001)
        except Timeout:
            raise UnknownError(*ERROR_MSG_0037)
        except RequestException as error:
            log.error(f'接口请求时发生未知错误，错误数据：{request_data.dict()}，报错内容：{error}')
            raise UnknownError(*ERROR_MSG_0002)
        try:
            response_json = response.json()
        except JSONDecodeError:
            response_json = None
        return ResponseDataModel(
            url=response.url,
            method=request_data.method,
            headers=request_data.headers,
            params=request_data.params,
            data=request_data.data,
            json_data=request_data.json_data,
            file=str(request_data.file),
            status_code=response.status_code,
            response_time=end,
            response_headers=response.headers,
            response_json=response_json,
            response_text=response.text
        )

    @classmethod
    def test_http(cls, request_data: RequestDataModel) -> Response:
        s = time.time()
        response = requests.request(
            method=request_data.method,
            url=request_data.url,
            headers=request_data.headers,
            params=request_data.params,
            data=request_data.data,
            json=request_data.json_data,
            files=request_data.file,
            timeout=int(30)
        )
        end = time.time() - s
        return response


if __name__ == '__main__':
    data = {"method": "POST",
            "url": "https://sara-test.growknows.cn/dev-api/aigc-order/goodsCouponsInfo/addGoodsCoupons",
            "headers": {
                "Authorization": "eyJhbGciOiJIUzUxMiJ9.eyJhY2Nlc3NfdG9rZW4iOiJCZWFyZXIgdG9rZW46bG9naW5fdG9rZW5zOjE6MjphY2Nlc3NfdG9rZW46NzJlNjEwNTgtNmY3NS00MDg5LTg4N2YtZWMyM2RkNmY4MTJjIiwicmVmcmVzaF90b2tlbiI6IkJlYXJlciB0b2tlbjpsb2dpbl90b2tlbnM6MToyOnJlZnJlc2hfdG9rZW46SC02SGRraDBDckkyUXUwSHlXelYybFM2YzlYenZLamZKQzlBMkU5NnJsWjgzQUhkTTRrbjlvZGhUNmVXU1paUDI2dHc3MEZLREhDR29xMWxtY3cxeTh2clpxV0lzU2F0MVRPSXZERHhIMXdCaUVIalBIYlpRRU04VjdQODdzcTciLCJhY2NvdW50X3R5cGUiOiJ2aXAiLCJ1c2VyX3R5cGUiOiIwMCIsInVzZXJfaWQiOjIsInVzZXJfbmFtZSI6ImFkbWluQGFpZ2MuY29tIiwiaXNfbGVzc29yIjoiWSIsImVudGVycHJpc2VfaWQiOjEsImVudGVycHJpc2VfbmFtZSI6ImFkbWluaXN0cmF0b3IiLCJzb3VyY2VfbmFtZSI6InNsYXZlIn0.h9VybBPjJVq5jZQFUhrWQ0vvwHP83x9yhlG0727p9_QywlBlWIhXtdnMFObysPUfuMMxX9lX1DPgk8Gbn6Qcpw",
                "content-type": "application/json"

            },
            "params": None,
            "data": None,
            "json_data": {"name": "自动化测试001", "expDate": "2024-04-04 00:00:00", "expType": "2",
                          "startDate": "2024-04-01 00:00:00", "couponsNum": 1, "couponsType": "1", "targetUsers": "",
                          "couponsRulesJson": {"frequency": 2, "exchangeCycle": "everyDay"},
                          "goodsDiscountsRuleIds": "1775381374142443522"}, "file": None}

    print(HTTPRequest.test_http(RequestDataModel(**data)).json())
