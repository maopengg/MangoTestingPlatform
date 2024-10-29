# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:11
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class CaseStepsDetailed(HttpBase):

    @classmethod
    @request_log()
    def get_case_steps_detailed(cls, page, page_size, params: dict = None):
        url = cls.url(f'/ui/case/steps/detailed')
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_case_steps_detailed(cls, json_data: dict):
        url = cls.url(f'/ui/case/steps/detailed')
        return cls.post(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_case_steps_detailed(cls, json_data: dict):
        url = cls.url(f'/ui/case/steps/detailed')
        return cls.put(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_case_steps_detailed(cls, _id, ):
        url = cls.url(f'/ui/case/steps/detailed')
        _params = {
            'id': _id,
        }
        return cls.delete(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_case_cache_data(cls, _id):
        url = cls.url(f'/ui/case/steps/refresh/cache/data')
        _params = {
            'id': _id,
        }
        if _params:
            _params.update(_params)
        return cls.get(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def put_case_sort(cls, case_sort_list: list[dict]):
        json_data = {
            'case_sort_list': case_sort_list,
        }
        url = cls.url(f'/ui/case/put/case/sort')
        return cls.put(url=url, headers=cls.headers, json=json_data)
