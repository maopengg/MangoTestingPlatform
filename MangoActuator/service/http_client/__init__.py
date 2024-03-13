# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-08-28 21:23
# @Author : 毛鹏
from urllib.parse import urljoin

import service


class HttpRequest:
    def __init__(self):
        self.ip = service.IP
        self.port = service.PORT
        self.username = service.USERNAME
        self.password = service.PASSWORD
        self.headers = {
            'Auth': ''
        }

    def url(self, url):
        return urljoin(f'http://{self.ip}:{self.port}', url)
