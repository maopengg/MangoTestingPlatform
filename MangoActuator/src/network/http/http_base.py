# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-12 18:09
# @Author : 毛鹏
from urllib.parse import urljoin

from mangokit import requests
from requests import Response

from src.models.socket_model import ResponseModel
from src.tools.decorator.request_log import request_log

HOST = ''


class HttpBase:
    headers = {
        'Authorization': ''
    }
    host = ''

    @classmethod
    def set_host(cls, ip=None, port=None, host=None):
        global HOST
        if ip and port:
            HOST = f'http://{ip}:{port}'
        else:
            HOST = host

    @classmethod
    @request_log()
    def get(cls, url, headers=None, **kwargs) -> ResponseModel | Response:
        return requests.get(urljoin(HOST, url), headers if headers else cls.headers, **kwargs)

    @classmethod
    @request_log()
    def post(cls, url, headers=None, **kwargs) -> ResponseModel | Response:
        return requests.post(urljoin(HOST, url), headers if headers else cls.headers, **kwargs)

    @classmethod
    @request_log()
    def put(cls, url, headers=None, **kwargs) -> ResponseModel | Response:
        return requests.put(urljoin(HOST, url), headers if headers else cls.headers, **kwargs)

    @classmethod
    @request_log()
    def delete(cls, url, headers=None, **kwargs) -> ResponseModel | Response:
        return requests.delete(urljoin(HOST, url), headers if headers else cls.headers, **kwargs)
