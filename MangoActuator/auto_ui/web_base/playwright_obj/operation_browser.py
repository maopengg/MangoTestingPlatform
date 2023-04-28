# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
from playwright.async_api import Page


class OperationBrowser:
    """
    浏览器操作类
    """
    web: Page = None
