# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-12 18:09
# @Author : 毛鹏
from urllib.parse import urljoin

import requests
from requests import Response

from src.models.socket_model import ResponseModel
from src.tools.decorator.request_log import request_log
from src.tools.set_config import SetConfig


class HttpBase:
    headers = {
        'Authorization': '',
    }

    @classmethod
    @request_log()
    def get(cls, url, headers=None, **kwargs) -> ResponseModel | Response:
        return requests.get(urljoin(SetConfig.get_host(), url),  # type: ignore
                            headers=headers if headers else cls.headers, proxies={'http': None, 'https': None},
                            **kwargs)

    @classmethod
    @request_log()
    def post(cls, url, headers=None, **kwargs) -> ResponseModel | Response:
        return requests.post(urljoin(SetConfig.get_host(), url),  # type: ignore
                             headers=headers if headers else cls.headers, proxies={'http': None, 'https': None},
                             **kwargs)

    @classmethod
    @request_log()
    def put(cls, url, headers=None, **kwargs) -> ResponseModel | Response:
        return requests.put(urljoin(SetConfig.get_host(), url),  # type: ignore
                            headers=headers if headers else cls.headers, proxies={'http': None, 'https': None},
                            **kwargs)

    @classmethod
    @request_log()
    def delete(cls, url, headers=None, **kwargs) -> ResponseModel | Response:
        return requests.delete(urljoin(SetConfig.get_host(), url),  # type: ignore
                               headers=headers if headers else cls.headers, proxies={'http': None, 'https': None},
                               **kwargs)
