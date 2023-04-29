# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-29 12:11
# @Author : 毛鹏
from playwright.sync_api import Page, Locator


class PlaywrightInputDevice:
    """输入设备，键盘和鼠标"""

    def __init__(self, page: Page = None):
        self.page = page

    def hover(self, selector):
        """鼠标悬停"""
        self.page.hover(selector)

    def keys(self, locator: Locator, keyboard: str):
        """按键"""
        locator.press(keyboard)
