# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:11
# @Author : 毛鹏
from src.models.network_model import ResponseModel
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class Config(HttpBase):

    @classmethod
    @request_log()
    def get_config(cls, page, page_size, params: dict = None):
        url = cls.url(f'/ui/config')
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        response = cls.get(url=url, headers=cls.headers, params=_params)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def post_config(cls, json_data: dict):
        url = cls.url(f'/ui/config')
        response = cls.post(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def put_config(cls, json_data: dict):
        url = cls.url(f'/ui/config')
        response = cls.put(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def delete_config(cls, _id, ):
        url = cls.url(f'/ui/config')
        _params = {
            'id': _id,
        }
        response = cls.delete(url=url, headers=cls.headers, params=_params)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def put_status(cls, id: int, status: int, is_headless: int | None = None):
        url = cls.url(f'/ui/config/put/status')
        json_data = {
            'status': status,
            'is_headless': is_headless,
            'id': id,

        }
        response = cls.put(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def new_browser_obj(cls, is_recording: str):
        url = cls.url(f'/ui/config/new/browser/obj')
        _params = {
            'is_recording': is_recording,
        }
        response = cls.get(url=url, headers=cls.headers,  params=_params)
        return ResponseModel(**response.json())
