# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class Role(HttpBase):
    _url = '/user/role'

    @classmethod
    def get_role(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(Role._url, params=_params)

    @classmethod
    def post_role(cls, json_data: dict):
        return cls.post(Role._url, json=json_data)

    @classmethod
    def put_role(cls, json_data: dict):
        return cls.put(Role._url, json=json_data)

    @classmethod
    def delete_role(cls, _id, ):
        return cls.delete(Role._url, params={'id': _id, })

    @classmethod
    def get_role_name(cls):
        return cls.get(f'{Role._url}/all')
