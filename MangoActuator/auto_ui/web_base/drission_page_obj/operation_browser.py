# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
from playwright.async_api import Page


class OperationBrowser:

    def __init__(self, web_obj: Page):
        self.web = web_obj
