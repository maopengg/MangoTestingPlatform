# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-07-26 上午10:03
# @Author : 毛鹏

from typing import Optional

from mangokit import requests
import time
from requests import Response
from requests.exceptions import *

from PyAutoTest.enums.system_enum import CacheDataKeyEnum
from PyAutoTest.exceptions import *
from PyAutoTest.models.api_model import RequestDataModel, ResponseDataModel
from PyAutoTest.tools.log_collector import log
from PyAutoTest.exceptions.error_msg import *


class BaseRequest:

    def __init__(self):
        from PyAutoTest.auto_test.auto_system.service.cache_data_value import CacheDataValue
        self.timeout = CacheDataValue.get_cache_value(CacheDataKeyEnum.API_TIMEOUT.name)
        self.response: Optional[Response | None] = None
        self.request_data: Optional[RequestDataModel | None] = None
        self.response_time: float = 0

    def request(self, request_data: RequestDataModel) -> Response:
        self.request_data = request_data
        log.api.info(self.request_data.model_dump_json())
        requests.timeout = int(self.timeout)
        try:
            s = time.time()
            self.response = requests.request(
                method=request_data.method,
                url=request_data.url,
                headers=request_data.headers,
                params=request_data.params,
                data=request_data.data,
                json=request_data.json_data,
                files=request_data.file,

            )
            self.response_time = time.time() - s
        except ProxyError:
            raise ApiError(*ERROR_MSG_0001)
        except SSLError:
            raise ApiError(*ERROR_MSG_0001)
        except Timeout:
            raise ApiError(*ERROR_MSG_0037)
        except RequestException as error:
            log.api.error(f'接口请求时发生未知错误，错误数据：{request_data.dict()}，报错内容：{error}')
            raise ApiError(*ERROR_MSG_0002)
        return self.response

    def request_result_data(self) -> ResponseDataModel:
        try:
            response_json = self.response.json()
            if isinstance(response_json, str):
                response_json = None
        except JSONDecodeError:
            response_json = None
        log.api.info(response_json if response_json else self.response.text)
        return ResponseDataModel(
            url=self.response.url,
            method=self.request_data.method,
            headers=self.request_data.headers,
            params=self.request_data.params,
            data=self.request_data.data,
            json_data=self.request_data.json_data,
            file=str(self.request_data.file) if self.request_data.file else None,
            status_code=self.response.status_code,
            response_time=self.response_time,
            response_headers=self.response.headers,
            response_json=response_json,
            response_text=self.response.text
        )

    @classmethod
    def test_http(cls, request_data: dict) -> Response:
        request_data = RequestDataModel(**request_data)
        return requests.request(
            method=request_data.method,
            url=request_data.url,
            headers=request_data.headers,
            params=request_data.params,
            data=request_data.data,
            json=request_data.json_data,
            files=request_data.file,
            timeout=int(30)
        )


if __name__ == '__main__':
    response = BaseRequest.test_http({"method": "POST", "url": "http://172.16.100.27:8819/login",
                                      "headers": {"Accept": "application/json, text/plain, */*",
                                                  "Content-Type": "application/json", "tenant_id": "14"},
                                      "params": None, "data": None, "json_data": None, "file": None})
    print(response.text)
