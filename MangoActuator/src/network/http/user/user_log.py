# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class UserLog(HttpBase):
    _url = 'user/user/logs'

    @classmethod
    def get_user_log(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(UserLog._url, params=_params)

    @classmethod
    def post_user_log(cls, json_data: dict):
        return cls.post(UserLog._url, json=json_data)

    @classmethod
    def put_user_log(cls, json_data: dict):
        return cls.put(UserLog._url, json=json_data)

    @classmethod
    def delete_user_log(cls, _id, ):
        return cls.delete(UserLog._url, params={'id': _id, })
