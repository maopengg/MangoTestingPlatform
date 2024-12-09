# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-08-28 21:23
# @Author : 毛鹏
import copy
import os

from src.enums.system_enum import ClientTypeEnum
from src.exceptions import ERROR_MSG_0007, ToolsError
from src.network.http.http_base import HttpBase
from src.tools import InitPath
from src.tools.log_collector import log


class HttpClientApi(HttpBase):
    @classmethod
    def download_file(cls, file_name):
        response = cls.get(f'files/{file_name}')
        file_path = InitPath.upload_files
        try:
            with open(fr'{file_path}\{file_name}', 'wb') as f:
                f.write(response.content)
        except FileNotFoundError:
            raise ToolsError(*ERROR_MSG_0007)

    @classmethod
    def upload_file(cls, project_product_id: int, file_path: str, file_name: str):
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
        response = cls.post('/user/file', headers=headers, data=data, files=files)
        if response.status_code == 200:
            return True
        else:
            log.error(f'上传文件报错，请管理员检查，响应结果：{response.text}')
            return False

    @classmethod
    def login(cls, username: str = None, password=None):
        response = cls.post('/login', data={
            'username': username,
            'password': password,
            'type': ClientTypeEnum.ACTUATOR.value
        })
        log.info(response.data)
        if response.data:
            cls.headers['Authorization'] = response.data.get('token')
        return response

    @classmethod
    def user_register(cls, json_data: dict):
        return cls.post('/register', json=json_data)
