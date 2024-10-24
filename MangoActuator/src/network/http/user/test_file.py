# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class TestFile(HttpBase):
    _url = 'user/file'

    @classmethod
    @request_log()
    def get_test_file(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=cls.url(TestFile._url), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_test_file(cls, json_data: dict):
        return cls.post(url=cls.url(TestFile._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_test_file(cls, json_data: dict):
        return cls.put(url=cls.url(TestFile._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_test_file(cls, _id, ):
        return cls.delete(url=cls.url(TestFile._url), headers=cls.headers, params={'id': _id, })
