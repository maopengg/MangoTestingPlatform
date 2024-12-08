# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class Project(HttpBase):
    _url = '/user/project'

    @classmethod
    @request_log()
    def get_project(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=cls.url(Project._url), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_project(cls, json_data: dict):
        return cls.post(url=cls.url(Project._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_project(cls, json_data: dict):
        return cls.put(url=cls.url(Project._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_project(cls, _id, ):
        _params = {
            'id': _id,
        }
        return cls.delete(url=cls.url(Project._url), headers=cls.headers, params=_params)
