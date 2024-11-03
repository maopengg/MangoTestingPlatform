# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-21 11:19
# @Author : 毛鹏
import copy
import json

from src.enums.tools_enum import ClientTypeEnum
from src.models.user_model import UserModel
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log
from src.tools.log_collector import log


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
        log.info(response.text)
        response_dict = response.json()
        if response_dict.get('data'):
            cls.headers['Authorization'] = response_dict.get('data').get('token')
            user_model = cls.get_userinfo(response_dict['data']['userId'])
            log.debug(f'用户配置：{user_model.model_dump_json()}')
        return response

    @classmethod
    @request_log()
    def user_register(cls, json_data: dict):
        return cls.post(cls.url('/register'), json=json_data)

    @classmethod
    def get_userinfo(cls, _id: int):
        url = cls.url(f'/user/info?id={_id}')
        response = cls.get(url=url, headers=cls.headers)
        if response.json().get('data'):
            user_info: dict = response.json()['data'][0]
            cls.headers['Project'] = str(user_info.get('selected_project')) if user_info.get(
                'selected_project') else None
            if user_info.get('config') is None:
                user_info['config'] = {}
                cls.put_user_info(copy.deepcopy(user_info))
            return UserModel(**user_info)

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
    @request_log()
    def post_user_info(cls, json_data: dict):
        url = cls.url(f'/user/info')
        return cls.post(url=url, headers=cls.headers, json=json_data)

    @classmethod
    @request_log()
    def put_user_info(cls, json_data: dict):
        url = cls.url(f'/user/info')
        if json_data.get('mailbox') and isinstance(json_data.get('mailbox'), str):
            json_data['mailbox'] = json.loads(json_data.get('mailbox'))
        for k, v in json_data.items():
            if isinstance(v, dict) and v.get('id'):
                json_data[k] = v.get('id')
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
