# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class Database(HttpBase):
    _url = '/system/database'

    @classmethod
    def get_database(cls, page=1, page_size=100, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(Database._url, params=_params)

    @classmethod
    def post_database(cls, json_data: dict):
        return cls.post(Database._url, json=json_data)

    @classmethod
    def put_database(cls, json_data: dict):
        return cls.put(Database._url, json=json_data)

    @classmethod
    def delete_database(cls, _id, ):
        return cls.delete(Database._url, params={'id': _id})

    @classmethod
    def put_database_status(cls, _id: int, environment: int, status: int):
        return cls.put(f'{Database._url}/status', json={
            'id': _id,
            'status': status,
            'test_object': environment
        })

    @classmethod
    def get_database_test(cls, _id):
        return cls.get(f'{Database._url}/test', params={'id': _id})
