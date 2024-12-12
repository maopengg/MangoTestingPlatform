# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class Tasks(HttpBase):
    _url = 'system/tasks'

    @classmethod
    def get_tasks(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(Tasks._url, params=_params)

    @classmethod
    def post_tasks(cls, json_data: dict):
        return cls.post(Tasks._url, json=json_data)

    @classmethod
    def put_tasks(cls, json_data: dict):
        return cls.put(Tasks._url, json=json_data)

    @classmethod
    def delete_tasks(cls, _id, ):
        return cls.delete(Tasks._url, params={'id': _id, })

    @classmethod
    def put_status(cls, _id, status):
        return cls.put(f'{Tasks._url}/status', params={'id': _id, 'status': status})

    @classmethod
    def put_notice(cls, _id, status):
        return cls.put(f'{Tasks._url}/notice', params={'id': _id, 'status': status})

    @classmethod
    def get_id_name(cls, case_type, ):
        return cls.put(f'{Tasks._url}/name', params={'case_type': case_type})

    @classmethod
    def trigger_timing(cls, _id, ):
        return cls.get(f'{Tasks._url}/trigger/timing', params={'id': _id})
