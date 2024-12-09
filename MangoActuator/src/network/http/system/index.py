# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-24 14:36
# @Author : 毛鹏

from src.network.http.http_base import HttpBase


class Index(HttpBase):
    _url = '/system/index'

    @classmethod
    def case_run_trends(cls):
        return cls.get(f'{Index._url}/result/week/sum', cls.headers)

    @classmethod
    def case_run_sum(cls):
        return cls.get(f'{Index._url}/run/sum', cls.headers)

    @classmethod
    def case_sum(cls):
        return cls.get(f'{Index._url}/sum', cls.headers)

    @classmethod
    def activity_level(cls):
        return cls.get(f'{Index._url}/activity/level', cls.headers)
