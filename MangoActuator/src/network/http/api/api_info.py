# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-05 11:16
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class ApiInfo(HttpBase):
    _url = '/api/info'

    @classmethod
    def get_api_info(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(ApiInfo._url, params=_params)

    @classmethod
    def post_api_info(cls, json_data: dict):
        return cls.post(ApiInfo._url, json=json_data)

    @classmethod
    def put_api_info(cls, json_data: dict):
        return cls.put(ApiInfo._url, json=json_data)

    @classmethod
    def delete_api_info(cls, _id, ):
        return cls.delete(ApiInfo._url, params={
            'id': _id
        })

    @classmethod
    def get_api_run(cls, _id, test_env, _id_list: list = None):
        _params = {
            'id': _id,
            'test_env': test_env,
        }
        if _id_list:
            _params['id'] = _id_list
        return cls.get(f'{ApiInfo._url}/test', params=_params)

    @classmethod
    def get_api_name(cls, module_id):
        return cls.get(f'{ApiInfo._url}/name', params={
            'module_id': module_id,
        })

    @classmethod
    def put_api_type(cls, type: int, id_list: list):
        return cls.put(f'{ApiInfo._url}/type', json={
            'id_list': id_list,
            'type': type,
        })

    @classmethod
    def post_copy_api_info(cls, _id: int):
        return cls.post(f'{ApiInfo._url}/copy', json={
            'id': _id,
        })

    @classmethod
    def post_import_api_info(cls, _json: dict):
        return cls.post(f'{ApiInfo._url}/import/api', json=_json)
