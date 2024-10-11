# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class Product(HttpBase):
    _url='/user/product'

    @classmethod
    @request_log()
    def get_product(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=cls.url(Product._url), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_product(cls, json_data: dict):
        return cls.post(url=cls.url(Product._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_product(cls, json_data: dict):
        return cls.put(url=cls.url(Product._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_product(cls, _id, ):
        return cls.delete(url=cls.url(Product._url), headers=cls.headers, params={'id': _id,})
