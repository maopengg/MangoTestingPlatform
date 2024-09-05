# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-08-28 21:23
# @Author : 毛鹏
import copy
import os

from src.enums.tools_enum import ClientTypeEnum
from src.exceptions.error_msg import ERROR_MSG_0007
from src.exceptions.tools_exception import FileNotError
from src.network import HttpRequest
from src.tools import InitPath
from src.tools.decorator.request_log import request_log
from src.tools.log_collector import log
from src.tools.other.path import Path


class HttpClient(HttpRequest):

    @classmethod
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
        return response_dict

    @classmethod
    def project_info(cls):
        url = cls.url('/user/project/product/name')
        response = cls.get(url=url, headers=cls.headers)
        response_dict = response.json()
        return response_dict

    @classmethod
    @request_log()
    def download_file(cls, file_name):
        url = cls.url(f'files/{file_name}')
        response = cls.get(url, headers=cls.headers)
        file_path = InitPath.upload_files
        file_path = Path.ensure_path_sep(rf'{file_path}\{file_name}')
        try:
            with open(file_path, 'wb') as f:
                f.write(response.content)
        except FileNotFoundError:
            raise FileNotError(*ERROR_MSG_0007)

    @classmethod
    @request_log()
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
        response = cls.post(url, headers=headers, data=data, files=files)
        if response.status_code == 200:
            return True
        else:
            log.error(f'上传文件报错，请管理员检查，响应结果：{response.text}')
            return False


if __name__ == '__main__':
    username1 = 'admin'
    password1 = 'as123456'
    HttpClient.login(username1, password1)
    HttpClient.download_file('author.jpg')
