# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-08-28 21:23
# @Author : 毛鹏
import copy
import os.path
import time
import traceback
from urllib.parse import urljoin

import requests
from mangotools.data_processor import EncryptionTool
from requests.exceptions import MissingSchema
from src.enums.system_enum import ClientTypeEnum
from src.exceptions import ERROR_MSG_0007, ToolsError, ERROR_MSG_0002, ERROR_MSG_0003, ERROR_MSG_0004
from src.network.http.http_base import HttpBase
from src.settings import settings
from src.tools import project_dir
from src.tools.log_collector import log
from src.tools.set_config import SetConfig


class HttpClientApi(HttpBase):

    @classmethod
    def download_file(cls, file_name):
        if SetConfig.get_is_minio():
            minio_host = SetConfig.get_minio_url()  # type: ignore
            if minio_host is None:
                raise ToolsError(*ERROR_MSG_0002)
        else:
            minio_host = SetConfig.get_host()
        url = urljoin(minio_host, f'/mango-file/test_file/{file_name}')
        response = requests.get(url, proxies={'http': None, 'https': None}, )
        try:
            if response.status_code != 200:
                raise ToolsError(*ERROR_MSG_0004, value=(file_name,))
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
            'name': file_name,
            'screenshot': True,
            'file_path': os.path.join('mango-file', 'failed_screenshot', file_name),
        }
        files = [
            ('failed_screenshot', (file_name, open(file_path, 'rb'), 'application/octet-stream'))
        ]
        for i in range(3):
            headers = copy.copy(cls.headers)
            response = cls.post('/system/file', headers=headers, data=data, files=files)
            if response.code == 200:
                return response.data
            else:
                log.error(f'上传文件报错，请管理员检查，响应结果：{response.model_dump()}')
                cls.login(SetConfig.get_username(), SetConfig.get_password())  # type: ignore

    @classmethod
    def login(cls, username: str = None, password=None, retry=0):
        try:
            response = cls.post('/login', data={
                'username': username,
                'password': EncryptionTool.md5_32_small(password),
                'version': settings.SETTINGS.get('version')
            })
            if response.data and response.code == 200:
                log.info(response.model_dump())
                cls.headers['Authorization'] = response.data.get('token')
            return response
        except Exception as error:
            if settings.IS_OPEN and retry < 100:
                time.sleep(3)
                log.info(f'开始登录重试：{retry}，{error}')
                return cls.login(username, password, retry + 1)
            else:
                raise error

    @classmethod
    def user_register(cls, json_data: dict):
        return cls.post('/register', json=json_data)


if __name__ == '__main__':
    HttpClientApi.download_file('蒲公英代下单字段模版-成功场景_.xlsx')
