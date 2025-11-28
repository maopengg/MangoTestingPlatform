# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class CacheData(HttpBase):
    _url = '/system/cache/data'

    @classmethod
    def get_cache_data(cls, page=1, page_size=100, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(CacheData._url, params=_params)

    @classmethod
    def post_cache_data(cls, json_data: dict):
        return cls.post(CacheData._url, json=json_data)

    @classmethod
    def put_cache_data(cls, json_data: dict | list):
        return cls.put(CacheData._url, json=json_data)

    @classmethod
    def delete_cache_data(cls, _id, ):
        return cls.delete(CacheData._url, params={'id': _id})
