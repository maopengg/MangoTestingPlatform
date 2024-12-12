# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:12
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class PageStepsDetailed(HttpBase):
    _url = '/ui/page/steps/detailed'

    @classmethod
    def get_page_steps_detailed(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(PageStepsDetailed._url, params=_params)

    @classmethod
    def post_page_steps_detailed(cls, json_data: dict):
        return cls.post(PageStepsDetailed._url, json=json_data)

    @classmethod
    def put_page_steps_detailed(cls, json_data: dict):
        return cls.put(PageStepsDetailed._url, json=json_data)

    @classmethod
    def delete_page_steps_detailed(cls, _id, ):
        return cls.delete(PageStepsDetailed._url, params={
            'id': _id,
        })

    @classmethod
    def put_step_sort(cls, step_sort_list: list[dict]):
        """ {id:1, step_sort:1 }"""
        return cls.put(f'{PageStepsDetailed._url}/sort', json={
            'step_sort_list': step_sort_list,
        })
