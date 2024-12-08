# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class Notice(HttpBase):
    _url = '/system/notice'

    @classmethod
    @request_log()
    def get_notice(cls, page=1, page_size=100, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=cls.url(Notice._url), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_notice(cls, json_data: dict):
        return cls.post(url=cls.url(Notice._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_notice(cls, json_data: dict):
        return cls.put(url=cls.url(Notice._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_notice(cls, _id, ):
        return cls.delete(url=cls.url(Notice._url), headers=cls.headers, params={'id': _id, })

    @classmethod
    @request_log()
    def put_notice_status(cls, _id: int, environment: int, status: int):
        return cls.put(url=cls.url(f'{Notice._url}/status'), headers=cls.headers,
                       json={'id': _id, 'status': status, 'test_object': environment})

    @classmethod
    @request_log()
    def get_notice_test(cls, _id):
        return cls.get(url=cls.url(f'{Notice._url}/test'), headers=cls.headers, params={'id': _id})
