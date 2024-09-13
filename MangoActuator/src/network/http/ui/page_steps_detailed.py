# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-13 11:12
# @Author : 毛鹏
from src.models.network_model import ResponseModel
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class PageStepsDetailed(HttpBase):

    @classmethod
    @request_log()
    def get_page_detailed(cls, page, page_size, params: dict = None):
        url = cls.url(f'/ui/steps/detailed')
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
    def post_page_detailed(cls, json_data: dict):
        url = cls.url(f'/ui/steps/detailed')
        response = cls.post(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def put_page_detailed(cls, json_data: dict):
        url = cls.url(f'/ui/steps/detailed')
        response = cls.put(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def delete_page_detailed(cls, _id, ):
        url = cls.url(f'/ui/steps/detailed')
        _params = {
            'id': _id,
        }
        response = cls.delete(url=url, headers=cls.headers, params=_params)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def put_step_sort(cls, step_sort_list: list[dict]):
        """ {id:1, step_sort:1 }"""
        url = cls.url(f'/ui/page/put/step/sort')
        json_data = {
            'step_sort_list': step_sort_list,
        }
        response = cls.put(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())
