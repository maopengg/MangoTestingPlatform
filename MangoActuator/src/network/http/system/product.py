# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class Product(HttpBase):
    _url = '/user/product'

    @classmethod
    def get_product(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(Product._url, params=_params)

    @classmethod
    def post_product(cls, json_data: dict):
        return cls.post(Product._url, json=json_data)

    @classmethod
    def put_product(cls, json_data: dict):
        return cls.put(Product._url, json=json_data)

    @classmethod
    def delete_product(cls, _id, ):
        return cls.delete(Product._url, params={'id': _id, })

    @classmethod
    def get_product_name(cls, project_id):
        return cls.get(f'{Product._url}/name', params={'project_id': project_id})

    @classmethod
    def product_all_module_name(cls, project_id):
        return cls.get(f'{Product._url}/all/module/name', params={'project_id': project_id})
