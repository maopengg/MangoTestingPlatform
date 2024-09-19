# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:11
# @Author : 毛鹏
from src.models.network_model import ResponseModel
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class EleResult(HttpBase):

    @classmethod
    @request_log()
    def get_ele_result(cls, page, page_size, params: dict = None):
        url = cls.url(f'/ui/ele/result')
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
    def post_ele_result(cls, json_data: dict):
        url = cls.url(f'/ui/ele/result')
        response = cls.post(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def put_ele_result(cls, json_data: dict):
        url = cls.url(f'/ui/ele/result')
        response = cls.put(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def delete_ele_result(cls, _id, ):
        url = cls.url(f'/ui/ele/result')
        _params = {
            'id': _id,
        }
        response = cls.delete(url=url, headers=cls.headers, params=_params)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def get_ele_result(cls, test_suite_id, case_id, page_step_id):
        url = cls.url(f'/ui/ele/result/ele')
        _params = {
            'test_suite_id': test_suite_id,
            'case_id': case_id,
            'page_step_id': page_step_id
        }
        response = cls.get(url=url, headers=cls.headers, params=_params)
        return ResponseModel(**response.json())
