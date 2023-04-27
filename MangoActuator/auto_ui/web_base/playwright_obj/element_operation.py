# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-26 22:22
# @Author : 毛鹏
from playwright.async_api import Page, Locator


class ElementOperation:
    """
    元素操作类
    """

    def __init__(self, web_obj: Page):
        self.web = web_obj


    def click(self, locating: Locator):
        locating.click()

    def input(self, locating: Locator, value: str):
        locating.fill(value)
