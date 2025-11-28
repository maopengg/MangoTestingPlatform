# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-21 11:19
# @Author : 毛鹏
import json

from src.models.user_model import UserModel
from src.network.http.http_base import HttpBase


class User(HttpBase):
    _url = 'user/info'

    @classmethod
    def get_user_info(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(User._url, params=_params)

    @classmethod
    def post_user_info(cls, json_data: dict):
        return cls.post(User._url, json=json_data)

    @classmethod
    def put_user_info(cls, json_data: dict):
        if json_data.get('mailbox') and isinstance(json_data.get('mailbox'), str):
            json_data['mailbox'] = json.loads(json_data.get('mailbox'))
        for k, v in json_data.items():
            if isinstance(v, dict) and v.get('id'):
                json_data[k] = v.get('id')
        return cls.put(User._url, json=json_data)

    @classmethod
    def delete_user_info(cls, _id, ):
        return cls.delete(User._url, params={
            'id': _id,
        })

    @classmethod
    def get_userinfo(cls, _id: int):
        response = cls.get(f'/user/info?id={_id}')
        if response.data:
            user_model = UserModel(**response.data[0])
            if user_model.selected_project:
                cls.headers['Project'] = str(user_model.selected_project)
            if user_model.config is None:
                user_model.config = {}
                cls.put_user_info(response.data[0])
        return response

    @classmethod
    def put_user_project(cls, _id, selected_project):
        return cls.put(f'{User._url}/project', json={
            'id': _id,
            'selected_project': selected_project
        })

    @classmethod
    def put_environment(cls, _id, selected_environment):
        return cls.put(f'{User._url}/environment', json={
            'id': _id,
            'selected_environment': selected_environment
        })

    @classmethod
    def put_password(cls, _id, password: str, new_password: str, confirm_password: str):
        return cls.put(f'{User._url}/password', json={
            'id': _id,
            'password': password,
            'new_password': new_password,
            'confirm_password': confirm_password,
        })

    @classmethod
    def get_name(cls, ):
        return cls.get(f'{User._url}/name', )
