# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
from auto_ui.web_base.playwright_base import PlaywrightBase


class PlaywrightPageOperation(PlaywrightBase):
    """浏览器操作类"""

    def goto(self, url: str):
        """
        打开url
        @param url: 打开的指定url
        @return:
        """
        self.page.goto(url, timeout=50000)

    def screenshot(self, path: str, full_page=True):
        """整个页面截图"""
        self.page.screenshot(path=path, full_page=full_page)
