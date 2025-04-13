# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-08-28 21:23
# @Author : 毛鹏
import copy

from mangokit.apidrive import requests

from src.enums.system_enum import ClientTypeEnum
from src.exceptions import ERROR_MSG_0007, ToolsError
from src.network.http.http_base import HttpBase
from src.settings.settings import FILE_PATH
from src.tools import project_dir
from src.tools.log_collector import log


class HttpClientApi(HttpBase):
    @classmethod
    def download_file(cls, file_name):
        response = requests.get(f'{FILE_PATH()}/test_file/{file_name}', cls.headers)
        file_path = project_dir.upload()
        try:
            with open(fr'{file_path}\{file_name}', 'wb') as f:
                f.write(response.content)
        except FileNotFoundError:
            raise ToolsError(*ERROR_MSG_0007)

    @classmethod
    def upload_file(cls, file_path: str, file_name: str):
        data = {
            'type': ClientTypeEnum.ACTUATOR.value,
            'name': file_name
        }
        files = [
            ('failed_screenshot', (file_name, open(file_path, 'rb'), 'application/octet-stream'))
        ]
        headers = copy.copy(cls.headers)
        response = cls.post('/system/file', headers=headers, data=data, files=files)
        if response.code == 200:
            return True
        else:
            log.error(f'上传文件报错，请管理员检查，响应结果：{response.model_dump()}')
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


if __name__ == '__main__':
    HttpClientApi.set_host('')
    HttpClientApi.upload_file(
        'D:\GitCode\MangoTestingPlatform\MangoActuator\screenshot\失败截图-下载铃铛1741762773000.jpg',
        '失败截图-下载铃铛1741762773000.jpg')
