# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class TasksDetails(HttpBase):
    _url = 'system/tasks/run/case'

    @classmethod
    @request_log()
    def get_tasks_list(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=cls.url(TasksDetails._url), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_tasks_list(cls, json_data: dict):
        return cls.post(url=cls.url(TasksDetails._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_tasks_list(cls, json_data: dict):
        return cls.put(url=cls.url(TasksDetails._url), headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_tasks_list(cls, _id, ):
        return cls.delete(url=cls.url(TasksDetails._url), headers=cls.headers, params={'id': _id, })

    @classmethod
    @request_log()
    def get_tasks_type_case_name(cls, type, module_id):
        _params = {
            'type': type,
            'module_id': module_id
        }
        return cls.get(url=cls.url(f'{TasksDetails._url}/type/case/name'), headers=cls.headers, params=_params)
