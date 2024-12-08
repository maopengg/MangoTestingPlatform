# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-03 16:25
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class Page(HttpBase):
    _url = '/ui/page'

    @classmethod
    @request_log()
    def get_page(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(cls.url(Page._url), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_page(cls, json_data: dict):
        return cls.post(cls.url(Page._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_page(cls, json_data: dict):
        return cls.put(cls.url(Page._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_page(cls, _id, ):
        _params = {
            'id': _id,
        }
        return cls.delete(cls.url(Page._url), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def module_page_name(cls, module_id, ):
        _params = {
            'module_id': module_id,
        }
        return cls.get(cls.url(f'{Page._url}/name'), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def page_copy(cls, page_id, ):
        _json = {
            'page_id': page_id,
        }
        return cls.post(cls.url(f'{Page._url}/copy'), cls.headers, json=_json)
