# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-12 18:08
# @Author : 毛鹏

from .api import ApiApi
from .http_client import HttpClientApi
from .system import SystemApi
from .ui import UiApi
from .user import UserApi


class HTTP:
    api = ApiApi
    ui = UiApi
    user = UserApi
    system = SystemApi
    not_auth = HttpClientApi
