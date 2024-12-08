# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-05 11:17
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class ApiPublic(HttpBase):
    _url = '/api/public'

    @classmethod
    @request_log()
    def get_api_public(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=cls.url(ApiPublic._url), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_api_public(cls, json_data: dict):
        return cls.post(url=cls.url(ApiPublic._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_api_public(cls, json_data: dict):
        return cls.put(url=cls.url(ApiPublic._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_api_public(cls, _id, ):
        return cls.delete(url=cls.url(ApiPublic._url), headers=cls.headers, params={'id': _id})

    @classmethod
    @request_log()
    def put_api_public_status(cls, _id, status):
        return cls.put(
            url=cls.url(f'{ApiPublic._url}/status'),
            headers=cls.headers,
            json={'id': _id, 'status': status}
        )
