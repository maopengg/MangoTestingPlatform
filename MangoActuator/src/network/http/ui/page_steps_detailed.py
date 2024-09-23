# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:12
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class PageStepsDetailed(HttpBase):

    @classmethod
    @request_log()
    def get_page_steps_detailed(cls, page, page_size, params: dict = None):
        url = cls.url(f'/ui/page/steps/detailed')
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_page_steps_detailed(cls, json_data: dict):
        url = cls.url(f'/ui/page/steps/detailed')
        return cls.post(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_page_steps_detailed(cls, json_data: dict):
        url = cls.url(f'/ui/page/steps/detailed')
        return cls.put(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_page_steps_detailed(cls, _id, ):
        url = cls.url(f'/ui/page/steps/detailed')
        _params = {
            'id': _id,
        }
        return cls.delete(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def put_step_sort(cls, step_sort_list: list[dict]):
        """ {id:1, step_sort:1 }"""
        url = cls.url(f'/ui/page/put/step/sort')
        json_data = {
            'step_sort_list': step_sort_list,
        }
        return cls.put(url=url, headers=cls.headers, json=json_data)
