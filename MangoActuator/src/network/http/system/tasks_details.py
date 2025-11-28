# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class TasksDetails(HttpBase):
    _url = 'system/tasks/details'

    @classmethod
    def get_tasks_list(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(TasksDetails._url, params=_params)

    @classmethod
    def post_tasks_list(cls, json_data: dict):
        return cls.post(TasksDetails._url, json=json_data)

    @classmethod
    def put_tasks_list(cls, json_data: dict):
        return cls.put(TasksDetails._url, json=json_data)

    @classmethod
    def delete_tasks_list(cls, _id, ):
        return cls.delete(TasksDetails._url, params={'id': _id, })

    @classmethod
    def get_type_case_name(cls, _type, module_id):
        return cls.get(f'{TasksDetails._url}/type/case/name', params={
            'type': _type,
            'module_id': module_id
        })

    @classmethod
    def batch_set_cases(cls, case_id_list, tasks_id):
        return cls.post(f'{TasksDetails._url}/batch/set/cases', json={
            'case_id_list': case_id_list,
            'scheduled_tasks_id': tasks_id
        })

    @classmethod
    def put_tasks_case_test_object(cls, case_list, test_obj_id):
        return cls.put(f'{TasksDetails._url}/case/test/object', json={
            'case_list': case_list,
            'test_obj_id': test_obj_id
        })
