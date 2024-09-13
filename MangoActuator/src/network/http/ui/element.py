# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-13 11:11
# @Author : 毛鹏
from src.models.network_model import ResponseModel
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class Element(HttpBase):

    @classmethod
    @request_log()
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
    @request_log()
    def post_page_element(cls, json_data: dict):
        url = cls.url(f'/ui/element')
        response = cls.post(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def put_page_element(cls, json_data: dict):
        url = cls.url(f'/ui/element')
        response = cls.put(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def delete_page_element(cls, _id, ):
        url = cls.url(f'/ui/element')
        _params = {
            'id': _id,
        }
        response = cls.delete(url=url, headers=cls.headers, params=_params)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def test_element(cls, test_env, page_id, element_id):
        url = cls.url(f'/ui/element')
        json_data = {
            'test_env': test_env,
            'page_id': page_id,
            'id': element_id,
        }
        response = cls.post(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def get_element_name(cls, page_id, ):
        url = cls.url(f'/ui/element/name')
        _params = {
            'id': page_id,
        }
        response = cls.get(url, cls.headers, params=_params)
        return ResponseModel(**response.json())
