# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-24 14:36
# @Author : 毛鹏
from mangokit import requests

from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class Index(HttpBase):
    _url = '/system/index'

    @classmethod
    @request_log()
    def case_run_trends(cls):
        return requests.get(cls.url(f'{Index._url}/result/week/sum'), cls.headers)

    @classmethod
    @request_log()
    def case_run_sum(cls):
        return requests.get(cls.url(f'{Index._url}/run/sum'), cls.headers)

    @classmethod
    @request_log()
    def case_sum(cls):
        return requests.get(cls.url(f'{Index._url}/sum'), cls.headers)

    @classmethod
    @request_log()
    def case_sum(cls):
        return requests.get(cls.url(f'{Index._url}/activity/level'), cls.headers)
