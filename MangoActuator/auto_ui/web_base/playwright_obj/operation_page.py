# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
from playwright.async_api import Page


class PlaywrightPageOperation:
    """浏览器操作类"""

    def __init__(self, page: Page = None):
        self.page = page

    async def goto(self, url: str):
        """
        打开url
        @param url: 打开的指定url
        @return:
        """
        await self.page.goto(url, timeout=50000)

    async def screenshot(self, path: str, full_page=True):
        """整个页面截图"""
        await self.page.screenshot(path=path, full_page=full_page)

    # def ele_screenshot(self, selector: str, path: str):
    #     """元素截图"""
    #     await self.page.locator(selector).screenshot(path=path)
