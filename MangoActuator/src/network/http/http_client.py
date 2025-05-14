# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-08-28 21:23
# @Author : 毛鹏
import copy
import os.path
import traceback
from urllib.parse import urljoin

import time
from mangokit.apidrive import requests
from mangokit.data_processor import EncryptionTool
from requests.exceptions import MissingSchema

from src.enums.system_enum import ClientTypeEnum
from src.exceptions import ERROR_MSG_0007, ToolsError, ERROR_MSG_0001, ERROR_MSG_0002, ERROR_MSG_0003
from src.network.http.http_base import HttpBase
from src.settings import settings
from src.tools import project_dir
from src.tools.log_collector import log
from src.tools.set_config import SetConfig


class HttpClientApi(HttpBase):

    @classmethod
    def download_file(cls, file_name):
        minio_host = SetConfig.get_minio_url()  # type: ignore
        if minio_host is None:
            raise ToolsError(*ERROR_MSG_0002)
        response = requests.get(urljoin(minio_host, f'/mango-file/test_file/{file_name}'))
        try:
            if response.status_code != 200:
                raise ToolsError(*ERROR_MSG_0003)
            with open(os.path.join(project_dir.upload(), file_name), 'wb') as f:
                f.write(response.content)
        except FileNotFoundError:
            raise ToolsError(*ERROR_MSG_0007)
        except MissingSchema:
            raise ToolsError(*ERROR_MSG_0003)

    @classmethod
    def upload_file(cls, file_path: str, file_name: str):
        data = {
            'type': ClientTypeEnum.ACTUATOR.value,
            'name': file_name
        }
        files = [
            ('failed_screenshot', (file_name, open(file_path, 'rb'), 'application/octet-stream'))
        ]
        for i in range(3):
            headers = copy.copy(cls.headers)
            response = cls.post('/system/file', headers=headers, data=data, files=files)
            if response.code == 200:
                return True
            else:
                log.error(f'上传文件报错，请管理员检查，响应结果：{response.model_dump()}')
                cls.login(SetConfig.get_username(), SetConfig.get_password())  # type: ignore
        return False

    @classmethod
    def login(cls, username: str = None, password=None):
        try:
            response = cls.post('/login', data={
                'username': username,
                'password': EncryptionTool.md5_32_small(**{'data': password}),
                'type': ClientTypeEnum.ACTUATOR.value
            })
            if response.data and response.code == 200:
                log.info(response.model_dump())
                cls.headers['Authorization'] = response.data.get('token')
            return response
        except Exception as error:
            traceback.print_exc()
            if settings.IS_OPEN:
                time.sleep(3)
                cls.login(username, password)
            else:
                raise error

    @classmethod
    def user_register(cls, json_data: dict):
        return cls.post('/register', json=json_data)


if __name__ == '__main__':
    HttpClientApi.download_file('蒲公英代下单字段模版-成功场景_.xlsx')
