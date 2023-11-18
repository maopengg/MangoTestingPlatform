# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 封装请求
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import requests
from requests import Response

from PyAutoTest.models.apimodel import RequestDataModel


class HTTPRequest:

    @classmethod
    def http(cls, request_data: RequestDataModel) -> Response:
        print(request_data.json())
        return requests.request(method=request_data.method,
                                url=request_data.url,
                                headers=request_data.headers,
                                params=request_data.params,
                                data=request_data.file,
                                json=request_data.json_data,
                                files=request_data.file
                                )
