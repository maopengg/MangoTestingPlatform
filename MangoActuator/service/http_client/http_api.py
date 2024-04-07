# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-08-28 21:23
# @Author : 毛鹏
import requests

from enums.tools_enum import ClientTypeEnum
from exceptions.tools_exception import FileNotError
from service.http_client import HttpRequest
from tools import InitializationPath
from tools.message.error_msg import ERROR_MSG_0007
from tools.other.path import Path


class HttpApi(HttpRequest):

    def login(self):
        url = self.url('/login')
        data = {
            'username': self.username,
            'password': self.password,
            'type': ClientTypeEnum.ACTUATOR.value
        }
        response = requests.post(url=url, data=data)
        response_dict = response.json()
        self.headers['Auth'] = response_dict['data']['token']
        return response_dict

    def download_file(self, project_id, file_name):
        url = self.url('/user/files/download')
        params = {
            'file_name': f'{file_name}',
            'project_id': project_id
        }
        response = requests.request("GET", url, headers=self.headers, params=params)
        file_path = InitializationPath.upload_files
        file_path = Path.ensure_path_sep(rf'{file_path}\{file_name}')
        try:
            with open(file_path, 'wb') as f:
                f.write(response.content)
        except FileNotFoundError:
            raise FileNotError(*ERROR_MSG_0007)


if __name__ == '__main__':
    ip = '61.183.9.60'
    prot = 8001
    username = 17798339533
    password = 123456
    r = HttpApi(ip, prot, username, password)
    r.login()
    print(r.download_file(11, '文档库搜索112.pdf'))
