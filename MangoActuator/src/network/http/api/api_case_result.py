# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-13 10:42
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class ApiCaseResult(HttpBase):
    _url = '/api/result'

    @classmethod
    @request_log()
    def get_api_result(cls, page=1, page_size=100, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=cls.url(ApiCaseResult._url), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_api_result(cls, json_data: dict):
        return cls.post(url=cls.url(ApiCaseResult._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_api_result(cls, json_data: dict):
        return cls.put(url=cls.url(ApiCaseResult._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_api_result(cls, _id, ):
        return cls.delete(url=cls.url(ApiCaseResult._url), headers=cls.headers, params={'id': _id})

    @classmethod
    @request_log()
    def get_api_result_week(cls):
        return cls.get(url=cls.url(f'{ApiCaseResult._url}/week'), headers=cls.headers)

    @classmethod
    @request_log()
    def get_api_result_suite_case(cls, test_suite_id):
        return cls.get(url=cls.url(f'{ApiCaseResult._url}/suite/case'), headers=cls.headers,
                       params={'test_suite_id': test_suite_id})
