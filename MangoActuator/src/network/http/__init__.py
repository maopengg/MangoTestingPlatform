# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-12 18:08
# @Author : 毛鹏

from .http_client import HttpClientApi
from .user import UserApi

class HTTP:
    api = 'ApiApi'
    ui = 'UiApi'
    user = UserApi
    system = 'SystemApi'
    not_auth = HttpClientApi
