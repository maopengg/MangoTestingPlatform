# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class TestObject(HttpBase):
    _url = 'user/test/object'

    @classmethod
    @request_log()
    def get_test_object(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=cls.url(TestObject._url), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_test_object(cls, json_data: dict):
        return cls.post(url=cls.url(TestObject._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_test_object(cls, json_data: dict):
        return cls.put(url=cls.url(TestObject._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_test_object(cls, _id, ):
        _params = {
            'id': _id,
        }
        return cls.delete(url=cls.url(TestObject._url), headers=cls.headers, params=_params)
