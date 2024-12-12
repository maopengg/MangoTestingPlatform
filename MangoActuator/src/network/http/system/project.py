# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class Project(HttpBase):
    _url = '/system/project'

    @classmethod
    def get_project(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(Project._url, params=_params)

    @classmethod
    def post_project(cls, json_data: dict):
        return cls.post(Project._url, json=json_data)

    @classmethod
    def put_project(cls, json_data: dict):
        return cls.put(Project._url, json=json_data)

    @classmethod
    def delete_project(cls, _id, ):
        _params = {
            'id': _id,
        }
        return cls.delete(Project._url, params=_params)

    @classmethod
    def project_info(cls):
        return cls.get(f'{Project._url}/all')

    @classmethod
    def project_product_name(cls, client_type):
        return cls.get(f'{Project._url}/product/name', params={'client_type': client_type})

    @classmethod
    def project_environment_name(cls):
        return cls.get(f'{Project._url}/environment/name')
