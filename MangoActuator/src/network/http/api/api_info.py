# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-05 11:16
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class ApiInfo(HttpBase):
    _url = '/api/info'

    @classmethod
    @request_log()
    def get_api_info(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=cls.url(ApiInfo._url), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_api_info(cls, json_data: dict):
        return cls.post(url=cls.url(ApiInfo._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_api_info(cls, json_data: dict):
        return cls.put(url=cls.url(ApiInfo._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_api_info(cls, _id, ):
        return cls.delete(url=cls.url(ApiInfo._url), headers=cls.headers, params={'id': _id})

    @classmethod
    @request_log()
    def get_api_run(cls, _id, test_env, _id_list: list = None):
        _params = {
            'id': _id,
            'test_env': test_env,
        }
        if _id_list:
            _params['id'] = _id_list
        return cls.get(url=cls.url(f'{ApiInfo._url}/test'), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def get_api_name(cls, module_id):
        _params = {
            'module_id': module_id,
        }
        return cls.get(url=cls.url(f'{ApiInfo._url}/name'), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def put_api_type(cls, type: int, id_list: list):
        _json = {
            'id_list': id_list,
            'type': type,
        }
        return cls.put(url=cls.url(f'{ApiInfo._url}/type'), headers=cls.headers, json=_json)

    @classmethod
    @request_log()
    def post_copy_api_info(cls, _id: int):
        _json = {
            'id': _id,
        }
        return cls.post(url=cls.url(f'{ApiInfo._url}/copy'), headers=cls.headers, json=_json)

    @classmethod
    @request_log()
    def post_import_api_info(cls, _json: dict):
        return cls.post(url=cls.url(f'{ApiInfo._url}/import/api'), headers=cls.headers, json=_json)
