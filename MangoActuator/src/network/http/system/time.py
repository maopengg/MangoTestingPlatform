# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-02 15:47
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class Time(HttpBase):
    _url = '/system/time'

    @classmethod
    def get_time_tasks(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(Time._url, params=_params)

    @classmethod
    def post_time_tasks(cls, json_data: dict):
        return cls.post(Time._url, json=json_data)

    @classmethod
    def put_time_tasks(cls, json_data: dict):
        return cls.put(Time._url, json=json_data)

    @classmethod
    def delete_time_tasks(cls, _id, ):
        return cls.delete(Time._url, params={'id': _id, })

    @classmethod
    def system_time_name(cls):
        return cls.get(f'{Time._url}/name')
