# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-05 11:16
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class ApiCaseDetailed(HttpBase):
    _url = '/api/case/detailed'

    @classmethod
    def get_api_case_detailed(cls, page=1, page_size=100, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(ApiCaseDetailed._url, params=_params)

    @classmethod
    def post_api_case_detailed(cls, parent_id, json_data: dict):
        json_data['parent_id'] = parent_id
        return cls.post(ApiCaseDetailed._url, json=json_data)

    @classmethod
    def put_api_case_detailed(cls, parent_id, json_data: dict):
        json_data['parent_id'] = parent_id
        return cls.put(ApiCaseDetailed._url, json=json_data)

    @classmethod
    def delete_api_case_detailed(cls, _id, parent_id):
        return cls.delete(ApiCaseDetailed._url, params={
            'id': _id,
            'parent_id': parent_id
        })

    @classmethod
    def put_api_case_sort(cls, case_sort_list: list[dict]):
        return cls.put(f'{ApiCaseDetailed._url}/sort', json={
            'case_sort_list': case_sort_list
        })

    @classmethod
    def put_api_case_refresh(cls, _id: int):
        return cls.put(f'{ApiCaseDetailed._url}/refresh', json={
            'id': _id
        })
