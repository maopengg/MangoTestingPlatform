# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:11
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class CaseResult(HttpBase):

    @classmethod
    @request_log()
    def get_case_result(cls, page, page_size, params: dict = None):
        url = cls.url(f'/ui/case/result')
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_case_result(cls, json_data: dict):
        url = cls.url(f'/ui/case/result')
        return cls.post(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_case_result(cls, json_data: dict):
        url = cls.url(f'/ui/case/result')
        return cls.put(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_case_result(cls, _id, ):
        url = cls.url(f'/ui/case/result')
        _params = {
            'id': _id,
        }
        return cls.delete(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def suite_get_case(cls, test_suite_id):
        url = cls.url(f'/ui/case/result/suite/get/case')
        _params = {
            'test_suite_id': test_suite_id,
        }
        return cls.get(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def case_result_week_sum(cls, ):
        url = cls.url(f'/ui/result/week')
        return cls.get(url=url, headers=cls.headers, )
