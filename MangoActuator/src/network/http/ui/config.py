# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:11
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class Config(HttpBase):
    _url = '/ui/config'

    @classmethod
    @request_log()
    def get_config(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(cls.url(Config._url), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_config(cls, json_data: dict):
        url = cls.url(f'/ui/config')
        return cls.post(cls.url(Config._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_config(cls, json_data: dict):
        url = cls.url(f'/ui/config')
        return cls.put(cls.url(Config._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_config(cls, _id, ):
        url = cls.url(f'/ui/config')
        _params = {
            'id': _id,
        }
        return cls.delete(cls.url(Config._url), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def put_ui_config_status(cls, _id: int, status: int):
        json_data = {
            'status': status,
            'id': _id,
        }
        return cls.put(cls.url(f'{Config._url}/status'), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def new_browser_obj(cls, is_recording: str):
        _params = {
            'is_recording': is_recording,
        }
        return cls.get(cls.url(f'{Config._url}/new/browser'), headers=cls.headers, params=_params)
