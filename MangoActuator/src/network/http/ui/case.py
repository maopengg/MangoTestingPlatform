# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:11
# @Author : 毛鹏
from src.models.network_model import ResponseModel
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class Case(HttpBase):

    @classmethod
    @request_log()
    def get_case(cls, page, page_size, params: dict = None):
        url = cls.url(f'/ui/case')
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
    def post_case(cls, json_data: dict):
        url = cls.url(f'/ui/case')
        response = cls.post(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def put_case(cls, json_data: dict):
        url = cls.url(f'/ui/case')
        response = cls.put(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def delete_case(cls, _id, ):
        url = cls.url(f'/ui/case')
        _params = {
            'id': _id,
        }
        response = cls.delete(url=url, headers=cls.headers, params=_params)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def cody_case(cls, _id, ):
        url = cls.url(f'/ui/case/copy/case')
        json_data = {
            'case_id': _id,
        }
        response = cls.post(url=url, headers=cls.headers, json_data=json_data)
        return ResponseModel(**response.json())
    @classmethod
    @request_log()
    def ui_case_run(cls, _id,test_env ):
        url = cls.url(f'/ui/case/run')
        _params = {
            'id': _id,
            'test_env': test_env,
        }
        response = cls.post(url=url, headers=cls.headers, params=_params)
        return ResponseModel(**response.json())
    @classmethod
    @request_log()
    def ui_batch_run(cls, case_id_list, ):
        url = cls.url(f'/ui/case/run')
        _params = {
            'case_id_list[]': case_id_list,
        }
        response = cls.get(url=url, headers=cls.headers, params=_params)
        return ResponseModel(**response.json())
