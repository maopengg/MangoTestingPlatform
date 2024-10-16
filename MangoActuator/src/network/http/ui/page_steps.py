# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:12
# @Author : 毛鹏
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
        return cls.get(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_page_steps(cls, json_data: dict):
        url = cls.url(f'/ui/steps')
        return cls.post(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_page_steps(cls, json_data: dict):
        url = cls.url(f'/ui/steps')
        return cls.put(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_page_steps(cls, _id, ):
        url = cls.url(f'/ui/steps')
        _params = {
            'id': _id,
        }
        return cls.delete(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def put_type(cls, _id: int):
        url = cls.url(f'/ui/steps/put/type')
        json_data = {
            'id': _id,
        }
        return cls.put(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def get_case_name(cls, ):
        url = cls.url(f'/ui/case/name')
        return cls.get(url=url, headers=cls.headers)

    @classmethod
    @request_log()
    def ui_steps_run(cls, test_env, page_step_id):
        url = cls.url(f'/ui/steps/run')
        _params = {
            'te': test_env,
            'page_step_id': page_step_id,
        }
        return cls.get(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def get_page_steps_name(cls, page_id):
        url = cls.url(f'/ui/steps/page/steps/name')
        _params = {
            'page_id': page_id,
        }
        return cls.get(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def copy_page_steps(cls, page_step_id):
        url = cls.url(f'/ui/copy/page/steps')
        _params = {
            'page_id': page_step_id,
        }
        return cls.post(url=url, headers=cls.headers)
