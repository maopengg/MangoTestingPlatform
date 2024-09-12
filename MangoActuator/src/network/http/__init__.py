# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-12 18:08
# @Author : 毛鹏
from .http_client import HttpClient
from .http_ui import HttpUi


class Http(HttpUi, HttpClient):
    pass
