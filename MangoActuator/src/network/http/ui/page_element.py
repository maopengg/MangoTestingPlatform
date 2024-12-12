# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:11
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class Element(HttpBase):
    _url = '/ui/element'

    @classmethod
    def get_page_element(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(Element._url, params=_params)

    @classmethod
    def post_page_element(cls, json_data: dict):
        return cls.post(Element._url, json=json_data)

    @classmethod
    def put_page_element(cls, json_data: dict):
        return cls.put(Element._url, json=json_data)

    @classmethod
    def delete_page_element(cls, _id, ):
        return cls.delete(Element._url, params={
            'id': _id,
        })

    @classmethod
    def test_element(cls, test_env, page_id, element_id, project_product_id, _type, ope_key, ope_value):
        return cls.post(f'{Element._url}/test', json={
            'project_product_id': project_product_id,
            'test_env': test_env,
            'page_id': page_id,
            'id': element_id,
            'type': _type,
            'ope_key': ope_key,
            'ope_value': ope_value,
            'is_send': True
        })

    @classmethod
    def get_element_name(cls, page_id, ):
        return cls.get(f'{Element._url}/name', params={
            'id': page_id,
        })

    @classmethod
    def put_is_iframe(cls, _id, is_iframe):
        return cls.put(f'{Element._url}/iframe', params={
            'id': _id,
            'is_iframe': is_iframe,
        })
