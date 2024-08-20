# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-08-28 21:23
# @Author : 毛鹏
from urllib.parse import urljoin

import service_conn


class HttpRequest:
    headers = {
        'Authorization': ''
    }

    @classmethod
    def url(cls, url):
        return urljoin(f'http://{service_conn.IP}:{service_conn.PORT}', url)
