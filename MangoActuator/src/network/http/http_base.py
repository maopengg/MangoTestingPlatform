# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-12 18:09
# @Author : 毛鹏
from urllib.parse import urljoin

from src.settings import settings
from src.tools.base_request.request_tool import Requests


class HttpBase(Requests):
    headers = {
        'Authorization': ''
    }
    ip = ''
    port = ''
    username = ''
    password = ''

    @classmethod
    def url(cls, url):
        return urljoin(f'http://{settings.IP}:{settings.PORT}', url)
