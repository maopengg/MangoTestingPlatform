# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-05 11:16
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class ApiCaseDetailed(HttpBase):
    _url = '/api/case/detailed'

    @classmethod
    @request_log()
    def get_api_case_detailed(cls, page=1, page_size=100, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=cls.url(ApiCaseDetailed._url), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_api_case_detailed(cls, json_data: dict):
        return cls.post(url=cls.url(ApiCaseDetailed._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_api_case_detailed(cls, json_data: dict):
        return cls.put(url=cls.url(ApiCaseDetailed._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_api_case_detailed(cls, _id, ):
        return cls.delete(url=cls.url(ApiCaseDetailed._url), headers=cls.headers, params={'id': _id})

    @classmethod
    @request_log()
    def put_api_case_sort(cls, case_sort_list: list[dict]):
        _json = {
            'case_sort_list': case_sort_list
        }
        return cls.put(url=cls.url(f'api/put/case/sort'), headers=cls.headers, json=_json)

    @classmethod
    @request_log()
    def put_api_case_refresh(cls, _id: int):
        _json = {
            'id': _id
        }
        return cls.put(url=cls.url(f'api/put/refresh/api/info'), headers=cls.headers, json=_json)
