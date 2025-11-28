# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-05 11:17
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class ApiHeaders(HttpBase):
    _url = '/api/headers'

    @classmethod
    def get_api_headers(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(ApiHeaders._url, params=_params)

    @classmethod
    def post_api_headers(cls, json_data: dict):
        return cls.post(ApiHeaders._url, json=json_data)

    @classmethod
    def put_api_headers(cls, json_data: dict):
        return cls.put(ApiHeaders._url, json=json_data)

    @classmethod
    def delete_api_headers(cls, _id, ):
        return cls.delete(ApiHeaders._url, params={
            'id': _id
        })
