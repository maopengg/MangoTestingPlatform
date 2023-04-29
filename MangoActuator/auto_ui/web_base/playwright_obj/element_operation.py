# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-26 22:22
# @Author : 毛鹏
from playwright.async_api import Page, Locator


class PlaywrightElementOperation:
    """元素操作类"""

    def __init__(self, page: Page = None):
        self.page = page

    @classmethod
    def click(cls, locating: Locator):
        """元素点击"""
        locating.click()

    @classmethod
    def input(cls, locating: Locator, value: str):
        """元素输入"""
        locating.fill(value)

    def upload_files(self, locating: Locator, file_path: str):
        """点击元素上传文件"""
        with self.page.expect_file_chooser() as fc_info:
            locating.click()
        file_chooser = fc_info.value
        file_chooser.set_files(file_path)
