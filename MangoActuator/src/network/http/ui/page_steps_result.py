# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:13
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class PageStepsResult(HttpBase):

    @classmethod
    @request_log()
    def get_page(cls, page, page_size, params: dict = None):
        url = cls.url(f'/ui/page')
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_page(cls, json_data: dict):
        url = cls.url(f'/ui/page')
        return cls.post(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_page(cls, json_data: dict):
        url = cls.url(f'/ui/page')
        return cls.put(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_page(cls, _id, ):
        url = cls.url(f'/ui/page')
        _params = {
            'id': _id,
        }
        return cls.delete(url=url, headers=cls.headers, params=_params)
