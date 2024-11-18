# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:11
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class EleResult(HttpBase):

    @classmethod
    @request_log()
    def get_ele_result(cls, test_suite_id, page_step_id, case_id):
        url = cls.url(f'/ui/ele/result')
        _params = {
            'test_suite_id': test_suite_id,
            'page_step_id': page_step_id,
            'case_id': case_id
        }

        return cls.get(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_ele_result(cls, json_data: dict):
        url = cls.url(f'/ui/ele/result')
        return cls.post(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_ele_result(cls, json_data: dict):
        url = cls.url(f'/ui/ele/result')
        return cls.put(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_ele_result(cls, _id, ):
        url = cls.url(f'/ui/ele/result')
        _params = {
            'id': _id,
        }
        return cls.delete(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def get_ele_result(cls, test_suite_id, case_id, page_step_id):
        url = cls.url(f'/ui/ele/result/ele')
        _params = {
            'test_suite_id': test_suite_id,
            'case_id': case_id,
            'page_step_id': page_step_id
        }
        return cls.get(url=url, headers=cls.headers, params=_params)
