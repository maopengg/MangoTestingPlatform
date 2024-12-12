# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-05 11:17
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class ApiPublic(HttpBase):
    _url = '/api/public'

    @classmethod
    def get_api_public(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(ApiPublic._url, params=_params)

    @classmethod
    def post_api_public(cls, json_data: dict):
        return cls.post(ApiPublic._url, json=json_data)

    @classmethod
    def put_api_public(cls, json_data: dict):
        return cls.put(ApiPublic._url, json=json_data)

    @classmethod
    def delete_api_public(cls, _id, ):
        return cls.delete(ApiPublic._url, params={
            'id': _id
        })

    @classmethod
    def put_api_public_status(cls, _id, status):
        return cls.put(f'{ApiPublic._url}/status', json={
            'id': _id, 'status': status
        })
