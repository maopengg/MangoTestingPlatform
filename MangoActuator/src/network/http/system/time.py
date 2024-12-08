# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-02 15:47
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class Time(HttpBase):
    _url = '/system/time'

    @classmethod
    @request_log()
    def get_time_tasks(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=cls.url(Time._url), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_time_tasks(cls, json_data: dict):
        return cls.post(url=cls.url(Time._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_time_tasks(cls, json_data: dict):
        return cls.put(url=cls.url(Time._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_time_tasks(cls, _id, ):
        return cls.delete(url=cls.url(Time._url), headers=cls.headers, params={'id': _id, })

    @classmethod
    @request_log()
    def system_time_name(cls):
        return cls.get(url=cls.url(f'{Time._url}/name'), headers=cls.headers)
