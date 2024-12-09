# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:12
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class PageSteps(HttpBase):
    _url = '/ui/page/steps'

    @classmethod
    def get_page_steps(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(PageSteps._url, params=_params)

    @classmethod
    def post_page_steps(cls, json_data: dict):
        return cls.post(PageSteps._url, json=json_data)

    @classmethod
    def put_page_steps(cls, json_data: dict):
        return cls.put(PageSteps._url, json=json_data)

    @classmethod
    def delete_page_steps(cls, _id, ):
        return cls.delete(PageSteps._url, params={
            'id': _id,
        })

    @classmethod
    def ui_steps_run(cls, test_env, page_step_id, is_send=1):
        return cls.get(f'{PageSteps._url}/test', params={
            'te': test_env,
            'page_step_id': page_step_id,
            'is_send': is_send
        })

    @classmethod
    def get_page_steps_name(cls, page_id):
        return cls.get(f'{PageSteps._url}/name', params={
            'page_id': page_id,
        })

    @classmethod
    def copy_page_steps(cls, page_step_id):
        return cls.post(f'{PageSteps._url}/copy', json={
            'page_id': page_step_id,
        })
