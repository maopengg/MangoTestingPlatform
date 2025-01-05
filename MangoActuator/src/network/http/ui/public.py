# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:13
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class Public(HttpBase):
    _url = '/ui/public'

    @classmethod
    def get_public(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(Public._url, params=_params)

    @classmethod
    def post_public(cls, json_data: dict):
        return cls.post(Public._url, json=json_data)

    @classmethod
    def put_public(cls, json_data: dict):
        return cls.put(Public._url, json=json_data)

    @classmethod
    def delete_public(cls, _id, ):
        return cls.delete(Public._url, params={
            'id': _id,
        })

    @classmethod
    def put_status(cls, _id, status):
        return cls.put(f'{Public._url}/status', json={
            'id': _id,
            'status': status,
        })
