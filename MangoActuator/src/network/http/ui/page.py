# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-03 16:25
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class Page(HttpBase):
    _url = '/ui/page'

    @classmethod
    def get_page(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(Page._url, params=_params)

    @classmethod
    def post_page(cls, json_data: dict):
        return cls.post(Page._url, json=json_data)

    @classmethod
    def put_page(cls, json_data: dict):
        return cls.put(Page._url, json=json_data)

    @classmethod
    def delete_page(cls, _id, ):
        return cls.delete(Page._url, params={
            'id': _id,
        })

    @classmethod
    def module_page_name(cls, module_id, ):
        return cls.get(f'{Page._url}/name', params={
            'module_id': module_id,
        })

    @classmethod
    def page_copy(cls, page_id, ):
        return cls.post(f'{Page._url}/copy', json={
            'page_id': page_id,
        })
