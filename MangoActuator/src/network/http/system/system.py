# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class Tasks(HttpBase):
    _url = 'system'

    @classmethod
    def common_variable(cls):
        return cls.get(f'{Tasks._url}/variable/random/list')

    @classmethod
    def random_data(cls, name):
        return cls.get(f'{Tasks._url}/variable/value', params={'name': name})

    @classmethod
    def enum_api(cls):
        return cls.get(f'{Tasks._url}/enum')
