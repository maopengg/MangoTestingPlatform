# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
from playwright.async_api import Page


class PlaywrightOperationBrowser:
    """浏览器操作类"""

    def __init__(self, page: Page = None):
        self.page = page

    def wait_for_timeout(self, sleep: int):
        self.page.wait_for_timeout(sleep)
