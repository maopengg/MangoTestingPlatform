# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class TestSuite(HttpBase):
    _url = 'system/test/suite'

    @classmethod
    def get_test_suite(cls, page, page_size, params=None):
        if params is None:
            params = {'type': 0}
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(TestSuite._url, params=_params)

    @classmethod
    def post_test_suite(cls, json_data: dict):
        return cls.post(TestSuite._url, json=json_data)

    @classmethod
    def put_test_suite(cls, json_data: dict):
        return cls.put(TestSuite._url, json=json_data)

    @classmethod
    def delete_test_suite(cls, _id, ):
        return cls.delete(TestSuite._url, params={'id': _id, })
