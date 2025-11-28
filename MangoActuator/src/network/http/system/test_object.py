# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class TestObject(HttpBase):
    _url = 'system/test/object'

    @classmethod
    def get_test_object(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(TestObject._url, params=_params)

    @classmethod
    def post_test_object(cls, json_data: dict):
        return cls.post(TestObject._url, json=json_data)

    @classmethod
    def put_test_object(cls, json_data: dict):
        return cls.put(TestObject._url, json=json_data)

    @classmethod
    def delete_test_object(cls, _id, ):
        _params = {
            'id': _id,
        }
        return cls.delete(TestObject._url, params=_params)
