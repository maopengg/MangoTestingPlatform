# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:12
# @Author : 毛鹏
from src.models.network_model import ResponseModel
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class PageSteps(HttpBase):

    @classmethod
    @request_log()
    def get_page_steps(cls, page, page_size, params: dict = None):
        url = cls.url(f'/ui/steps')
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
    def post_page_steps(cls, json_data: dict):
        url = cls.url(f'/ui/steps')
        response = cls.post(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def put_page_steps(cls, json_data: dict):
        url = cls.url(f'/ui/steps')
        response = cls.put(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def delete_page_steps(cls, _id, ):
        url = cls.url(f'/ui/steps')
        _params = {
            'id': _id,
        }
        response = cls.delete(url=url, headers=cls.headers, params=_params)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def put_type(cls, _id: int):
        url = cls.url(f'/ui/steps/put/type')
        json_data = {
            'id': _id,
        }
        response = cls.put(url=url, headers=cls.headers, json=json_data)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def get_case_name(cls,):
        url = cls.url(f'/ui/case/name')
        response = cls.get(url=url, headers=cls.headers)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def ui_steps_run(cls,test_env, page_step_id):
        url = cls.url(f'/ui/steps/run')
        _params = {
            'te': test_env,
            'page_step_id': page_step_id,
        }
        response = cls.delete(url=url, headers=cls.headers, params=_params)
        return ResponseModel(**response.json())
    @classmethod
    @request_log()
    def get_page_steps_name(cls,page_id):
        url = cls.url(f'/ui/steps/page/steps/name')
        _params = {
            'page_id': page_id,
        }
        response = cls.delete(url=url, headers=cls.headers, params=_params)
        return ResponseModel(**response.json())

    @classmethod
    @request_log()
    def copy_page_steps(cls,page_step_id):
        url = cls.url(f'/ui/copy/page/steps')
        _params = {
            'page_id': page_step_id,
        }
        response = cls.post(url=url, headers=cls.headers)
        return ResponseModel(**response.json())
