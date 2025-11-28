# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-05 11:16
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class ApiCase(HttpBase):
    _url = '/api/case'

    @classmethod
    def get_api_case(cls, page=1, page_size=100, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(ApiCase._url, params=_params)

    @classmethod
    def post_api_case(cls, json_data: dict):
        return cls.post(ApiCase._url, json=json_data)

    @classmethod
    def put_api_case(cls, json_data: dict):
        return cls.put(ApiCase._url, json=json_data)

    @classmethod
    def delete_api_case(cls, _id, ):
        return cls.delete(ApiCase._url, params={
            'id': _id
        })

    @classmethod
    def get_api_test_case(cls, case_id, test_env, case_sort: int | None = None):
        return cls.get(f'{ApiCase._url}/test', params={
            'case_id': case_id,
            'test_env': test_env,
            'case_sort': case_sort,
        })

    @classmethod
    def get_api_test_case_batch(cls, case_id_list: list, test_env):
        return cls.post(f'{ApiCase._url}/batch', json={
            'test_env': test_env,
            'case_id_list': case_id_list,
        })

    @classmethod
    def case_copy(cls, case_id):
        return cls.post(f'{ApiCase._url}/copy', json={
            'case_id': case_id,
        })
