# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:11
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class Case(HttpBase):
    _url = '/ui/case'

    @classmethod
    def get_case(cls, page, page_size, params: dict = None):
        url = cls.url(f'/ui/case')
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(Case._url, params=_params)

    @classmethod
    def post_case(cls, json_data: dict):
        return cls.post(Case._url, json=json_data)

    @classmethod
    def put_case(cls, json_data: dict):
        return cls.put(Case._url, json=json_data)

    @classmethod
    def delete_case(cls, _id, ):
        return cls.delete(Case._url, params={
            'id': _id,
        })

    @classmethod
    def cody_case(cls, _id, ):
        return cls.post(f'{Case._url}/copy', json_data={
            'case_id': _id,
        })

    @classmethod
    def ui_test_case(cls, case_id, test_env):
        return cls.get(f'{Case._url}/test', params={
            'case_id': case_id,
            'test_env': test_env,
        })

    @classmethod
    def ui_test_case_batch(cls, case_id_list, test_env):
        return cls.post(f'{Case._url}/batch', json={
            'case_id_list': case_id_list,
            'test_env': test_env,
        })
