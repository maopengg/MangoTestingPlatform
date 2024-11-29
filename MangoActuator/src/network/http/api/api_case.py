# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-05 11:16
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class ApiCase(HttpBase):
    _url = '/api/case'

    @classmethod
    @request_log()
    def get_api_case(cls, page=1, page_size=100, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=cls.url(ApiCase._url), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_api_case(cls, json_data: dict):
        return cls.post(url=cls.url(ApiCase._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_api_case(cls, json_data: dict):
        return cls.put(url=cls.url(ApiCase._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_api_case(cls, _id, ):
        return cls.delete(url=cls.url(ApiCase._url), headers=cls.headers, params={'id': _id})

    @classmethod
    @request_log()
    def get_api_case(cls, page=1, page_size=100, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=cls.url(ApiCase._url), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_api_case(cls, json_data: dict):
        return cls.post(url=cls.url(ApiCase._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def get_api_test_case(cls, case_id, test_env, case_sort: int | None = None):
        _params = {
            'case_id': case_id,
            'test_env': test_env,
            'case_sort': case_sort,
        }
        return cls.get(url=cls.url(f'{ApiCase._url}/test'), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def get_api_test_case_batch(cls, case_id_list: list, test_env):
        _json = {
            'test_env': test_env,
            'case_id_list': case_id_list,
        }
        return cls.post(url=cls.url(f'{ApiCase._url}/batch'), headers=cls.headers, json=_json)

    @classmethod
    @request_log()
    def get_api_case_synchronous(cls, host: list, project_id):
        _params = {
            'host': host,
            'project_id': project_id,
        }
        return (cls.get(url=cls.url(f'{ApiCase._url}/synchronous'), headers=cls.headers, params=_params)
                @ classmethod)

    @classmethod
    @request_log()
    def get_api_case_copy(cls, case_id):
        _params = {
            'case_id': case_id,
        }
        return cls.get(url=cls.url(f'{ApiCase._url}/copy'), headers=cls.headers, params=_params)
