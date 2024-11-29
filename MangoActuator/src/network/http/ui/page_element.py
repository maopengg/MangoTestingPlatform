# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:11
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class Element(HttpBase):

    @classmethod
    @request_log()
    def get_page_element(cls, page, page_size, params: dict = None):
        url = cls.url(f'/ui/element')
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_page_element(cls, json_data: dict):
        url = cls.url(f'/ui/element')
        return cls.post(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_page_element(cls, json_data: dict):
        url = cls.url(f'/ui/element')
        return cls.put(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_page_element(cls, _id, ):
        url = cls.url(f'/ui/element')
        _params = {
            'id': _id,
        }
        return cls.delete(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def test_element(cls, test_env, page_id, element_id, project_product_id, _type, ope_key, ope_value):
        url = cls.url(f'/ui/element')
        json_data = {
            'project_product_id': project_product_id,
            'test_env': test_env,
            'page_id': page_id,
            'id': element_id,
            'type': _type,
            'ope_key': ope_key,
            'ope_value': ope_value,
            'is_send': True
        }
        return cls.post(url=f'{url}/test', headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def get_element_name(cls, page_id, ):
        url = cls.url(f'/ui/element/name')
        _params = {
            'id': page_id,
        }
        return cls.get(url, cls.headers, params=_params)
