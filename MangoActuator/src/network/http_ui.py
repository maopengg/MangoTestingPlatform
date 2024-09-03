# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-03 16:25
# @Author : 毛鹏
from src.models.service_http_model import ResponseModel
from src.network import HttpRequest


class HttpUi(HttpRequest):

    @classmethod
    def get_page(cls, page, page_size, params: dict = None):
        url = cls.url(f'/ui/page')
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        response = cls.get(url=url, headers=cls.headers, params=_params)
        return ResponseModel(**response.json())

    @classmethod
    def post_page(cls, json_data: dict):
        url = cls.url(f'/ui/page')
        response = cls.post(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    def put_page(cls, json_data: dict):
        url = cls.url(f'/ui/page')
        response = cls.put(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    def delete_page(cls, _id, ):
        url = cls.url(f'/ui/page')
        _params = {
            'id': _id,
        }
        response = cls.delete(url=url, headers=cls.headers, params=_params)
        return ResponseModel(**response.json())

    @classmethod
    def get_page_element(cls, page, page_size, params: dict = None):
        url = cls.url(f'/ui/element')
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        response = cls.get(url=url, headers=cls.headers, params=_params)
        return ResponseModel(**response.json())

    @classmethod
    def post_page_element(cls, json_data: dict):
        url = cls.url(f'/ui/element')
        response = cls.post(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    def put_page_element(cls, json_data: dict):
        url = cls.url(f'/ui/element')
        response = cls.put(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    def delete_page_element(cls, _id, ):
        url = cls.url(f'/ui/element')
        _params = {
            'id': _id,
        }
        response = cls.delete(url=url, headers=cls.headers, params=_params)
        return ResponseModel(**response.json())
