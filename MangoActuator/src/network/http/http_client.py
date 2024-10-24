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
from src.network.http.http_base import HttpBase
from src.tools import InitPath
from src.tools.decorator.request_log import request_log
from src.tools.log_collector import log


class HttpClient(HttpBase):

    @classmethod
    def project_info(cls):
        url = cls.url('/user/project/product/name?client_type=1')
        response = cls.get(url=url, headers=cls.headers)
        return response.json()

    @classmethod
    @request_log()
    def download_file(cls, file_name):
        url = cls.url(f'files/{file_name}')
        response = cls.get(url, headers=cls.headers)
        file_path = InitPath.upload_files
        try:
            with open(fr'{file_path}\{file_name}', 'wb') as f:
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
        response = cls.post(url, headers=headers, data=data, files=files)
        if response.status_code == 200:
            return True
        else:
            log.error(f'上传文件报错，请管理员检查，响应结果：{response.text}')
            return False


