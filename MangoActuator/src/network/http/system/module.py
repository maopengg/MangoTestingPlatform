# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class Module(HttpBase):
    _url = '/system/module'

    @classmethod
    def get_module(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(Module._url, params=_params)

    @classmethod
    def post_module(cls, json_data: dict):
        return cls.post(Module._url, json=json_data)

    @classmethod
    def put_module(cls, json_data: dict):
        return cls.put(Module._url, json=json_data)

    @classmethod
    def delete_module(cls, _id, ):
        return cls.delete(Module._url, params={'id': _id, })

    @classmethod
    def get_module_name(cls, project_product_id):
        return cls.get(f'{Module._url}/name', params={'project_product_id': project_product_id})
