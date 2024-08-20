# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
import asyncio

from playwright.async_api import Locator

from src.services.ui.base_tools.base_data import BaseData


class PlaywrightPage(BaseData):
    """页面操作"""

    async def w_switch_tabs(self, individual: int):
        """切换页签"""
        pages = self.context.pages
        await pages[int(individual)].bring_to_front()
        self.page = pages[int(individual)]
        await asyncio.sleep(1)

    async def w_close_current_tab(self):
        """关闭当前页签"""
        await asyncio.sleep(2)
        pages = self.context.pages
        await pages[-1].close()
        self.page = pages[0]

    async def open_new_tab_and_switch(self, locating: Locator):
        """点击并打开新页签"""
        await locating.click()
        await asyncio.sleep(2)
        pages = self.context.pages
        new_page = pages[-1]
        await new_page.bring_to_front()
        self.page = new_page
        await asyncio.sleep(1)
