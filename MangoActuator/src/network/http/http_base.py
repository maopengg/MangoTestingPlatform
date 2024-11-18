# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-12 18:09
# @Author : 毛鹏
from urllib.parse import urljoin

from mangokit import requests

from src.settings import settings


class HttpBase(requests):
    headers = {
        'Authorization': ''
    }

    @classmethod
    def url(cls, url):
        return urljoin(f'http://{settings.IP}:{settings.PORT}', url)
