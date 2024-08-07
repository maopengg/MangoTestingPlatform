# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-08-28 21:23
# @Author : 毛鹏
import copy
import os

import requests

from enums.tools_enum import ClientTypeEnum
from exceptions.tools_exception import FileNotError
from service_conn.http_conn import HttpRequest
from tools import InitPath
from tools.log_collector import log
from tools.message.error_msg import ERROR_MSG_0007
from tools.other.path import Path


class HttpApi(HttpRequest):

    @classmethod
    def login(cls, username: str = None, password=None):
        url = cls.url('/login')
        data = {
            'username': username,
            'password': password,
            'type': ClientTypeEnum.ACTUATOR.value
        }
        response = requests.post(url=url, data=data)
        response_dict = response.json()
        cls.headers['Authorization'] = response_dict['data']['token']
        return response_dict

    @classmethod
    def download_file(cls, file_name):
        url = cls.url(f'files/{file_name}')
        response = requests.request("GET", url, headers=cls.headers)
        file_path = InitPath.upload_files
        file_path = Path.ensure_path_sep(rf'{file_path}\{file_name}')
        try:
            with open(file_path, 'wb') as f:
                f.write(response.content)
        except FileNotFoundError:
            raise FileNotError(*ERROR_MSG_0007)

    @classmethod
    def upload_file(cls, project_product_id: int, file_path: str, file_name: str):
        url = cls.url('/user/file')
        file_size = os.path.getsize(file_path)
        data = {
            'type': ClientTypeEnum.ACTUATOR.value,
            'project_product_id': project_product_id,
            'price': file_size,
            'name': file_name
        }
        files = [
            ('file', (file_name, open(file_path, 'rb'), 'application/octet-stream'))
        ]
        headers = copy.copy(cls.headers)
        response = requests.post(url, headers=headers, data=data, files=files)
        if response.status_code == 200:
            return True
        else:
            log.error(f'上传文件报错，请管理员检查，响应结果：{response.text}')
            return False


if __name__ == '__main__':

    username1 = 'admin'
    password1 = 'as123456'
    HttpApi.login(username1, password1)
    HttpApi.download_file('author.jpg')
