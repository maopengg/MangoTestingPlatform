# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class Notice(HttpBase):
    _url = '/system/notice'

    @classmethod
    def get_notice(cls, page=1, page_size=100, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(Notice._url, params=_params)

    @classmethod
    def post_notice(cls, json_data: dict):
        return cls.post(Notice._url, json=json_data)

    @classmethod
    def put_notice(cls, json_data: dict):
        return cls.put(Notice._url, json=json_data)

    @classmethod
    def delete_notice(cls, _id, ):
        return cls.delete(Notice._url, params={'id': _id, })

    @classmethod
    def put_notice_status(cls, _id: int, environment: int, status: int):
        return cls.put(f'{Notice._url}/status', json={
            'id': _id,
            'status': status,
            'test_object': environment
        })

    @classmethod
    def get_notice_test(cls, _id):
        return cls.get(f'{Notice._url}/test', params={'id': _id})
