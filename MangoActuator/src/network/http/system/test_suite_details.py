# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class TestSuiteDetails(HttpBase):
    _url = 'system/test/suite/details'

    @classmethod
    def get_test_suite_details(cls, page, page_size, params=None):
        if params is None:
            params = {'type': 0}
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(TestSuiteDetails._url, params=_params)

    @classmethod
    def post_test_suite_details(cls, json_data: dict):
        return cls.post(TestSuiteDetails._url, json=json_data)

    @classmethod
    def put_test_suite_details(cls, json_data: dict):
        return cls.put(TestSuiteDetails._url, json=json_data)

    @classmethod
    def delete_test_suite_details(cls, _id, ):
        return cls.delete(TestSuiteDetails._url, params={'id': _id, })

    @classmethod
    def get_test_suite_report(cls, ):
        return cls.get(f'{TestSuiteDetails._url}/report', )

    @classmethod
    def get_all_retry(cls, test_suite_id):
        return cls.get(f'{TestSuiteDetails._url}/all/retry', params={'test_suite_id': test_suite_id})

    @classmethod
    def get_retry(cls, _id):
        return cls.get(f'{TestSuiteDetails._url}/retry', params={'id': _id})
