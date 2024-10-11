# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:13
# @Author : 毛鹏
from src.models.network_model import ResponseModel
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class Public(HttpBase):

    @classmethod
    @request_log()
    def get_public(cls, page, page_size, params: dict = None):
        url = cls.url(f'/ui/public')
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_public(cls, json_data: dict):
        url = cls.url(f'/ui/public')
        return cls.post(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_public(cls, json_data: dict):
        url = cls.url(f'/ui/public')
        return cls.put(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_public(cls, _id, ):
        url = cls.url(f'/ui/public')
        _params = {
            'id': _id,
        }
        return cls.delete(url=url, headers=cls.headers, params=_params)
    @classmethod
    @request_log()
    def put_status(cls, _id, status):
        url = cls.url(f'/ui/public')
        json_data = {
            'id': _id,
            'status': status,
        }
        return cls.put(url=url, headers=cls.headers, json_data=json_data)
