# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-21 11:19
# @Author : 毛鹏

from pydantic_core._pydantic_core import ValidationError

from src.enums.tools_enum import ClientTypeEnum
from src.models.user_model import UserModel
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class User(HttpBase):

    @classmethod
    @request_log()
    def login(cls, username: str = None, password=None):
        url = cls.url('/login')
        data = {
            'username': username,
            'password': password,
            'type': ClientTypeEnum.ACTUATOR.value
        }
        response = cls.post(url=url, data=data)
        response_dict = response.json()
        cls.headers['Authorization'] = response_dict['data']['token']
        cls.get_userinfo(response_dict['data']['userId'])
        return response

    @classmethod
    def get_userinfo(cls, _id: int):
        url = cls.url(f'/user/info?id={_id}')
        response = cls.get(url=url, headers=cls.headers)
        if response.json().get('data'):
            cls.headers['Project'] = str(response.json()['data'][0].get('selected_project'))
            try:
                user = UserModel()
                user.update(**response.json()['data'][0])
                return user
            except ValidationError:
                return UserModel(**response.json()['data'][0])

    @classmethod
    @request_log()
    def get_user_info(cls, page, page_size, params: dict = None):
        url = cls.url(f'/user/info')
        _params = {
            'page': page,
            'pageSize': page_size
        }
        if params:
            _params.update(params)
        return cls.get(url=url, headers=cls.headers, params=_params)

    @classmethod
    def post_user_info(cls, json_data: dict):
        url = cls.url(f'/user/info')
        return cls.post(url=url, headers=cls.headers, json=json_data)

    @classmethod
    def put_user_info(cls, json_data: dict):
        url = cls.url(f'/user/info')
        return cls.put(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def delete_user_info(cls, _id, ):
        url = cls.url(f'/user/info')
        _params = {
            'id': _id,
        }
        return cls.delete(url=url, headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def put_user_project(cls, _id, selected_project):
        url = cls.url(f'/user/project/put')
        json_data = {
            'id': _id,
            'selected_project': selected_project
        }
        return cls.put(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_environment(cls, _id, selected_environment):
        url = cls.url(f'/user/environment')
        json_data = {
            'id': _id,
            'selected_environment': selected_environment
        }
        return cls.put(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_password(cls, _id, password: str, new_password: str, confirm_password: str):
        url = cls.url(f'/user/password')
        json_data = {
            'id': _id,
            'password': password,
            'new_password': new_password,
            'confirm_password': confirm_password,
        }
        return cls.put(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def get_nickname(cls, ):
        return cls.get(url=cls.url(f'/user/nickname'), headers=cls.headers, )
