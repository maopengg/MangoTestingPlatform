# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:11
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class CaseStepsDetailed(HttpBase):
    _url = '/ui/case/steps/detailed'

    @classmethod
    def get_case_steps_detailed(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(CaseStepsDetailed._url, params=_params)

    @classmethod
    def post_case_steps_detailed(cls, json_data: dict):
        return cls.post(CaseStepsDetailed._url, json=json_data)

    @classmethod
    def put_case_steps_detailed(cls, json_data: dict):
        return cls.put(CaseStepsDetailed._url, json=json_data)

    @classmethod
    def delete_case_steps_detailed(cls, _id, ):
        return cls.delete(CaseStepsDetailed._url, params={
            'id': _id,
        })

    @classmethod
    def post_case_cache_data(cls, _id):
        _params = {
            'id': _id,
        }
        if _params:
            _params.update(_params)
        return cls.get(f'{CaseStepsDetailed._url}/refresh', params=_params)

    @classmethod
    def put_case_sort(cls, case_sort_list: list[dict]):
        return cls.put(f'{CaseStepsDetailed._url}/sort', json={
            'case_sort_list': case_sort_list,
        })
