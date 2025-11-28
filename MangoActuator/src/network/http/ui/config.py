# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:11
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class Config(HttpBase):
    _url = '/ui/config'

    @classmethod
    def get_config(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(Config._url, params=_params)

    @classmethod
    def post_config(cls, json_data: dict):
        return cls.post(Config._url, json=json_data)

    @classmethod
    def put_config(cls, json_data: dict):
        return cls.put(Config._url, json=json_data)

    @classmethod
    def delete_config(cls, _id, ):
        return cls.delete(Config._url, params={
            'id': _id,
        })

    @classmethod
    def put_ui_config_status(cls, _id: int, status: int):
        return cls.put(f'{Config._url}/status', json={
            'status': status,
            'id': _id,
        })

    @classmethod
    def new_browser_obj(cls, is_recording: str):
        return cls.get(f'{Config._url}/new/browser', params={
            'is_recording': is_recording,
        })
