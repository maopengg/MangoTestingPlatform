# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-04-25 22:33
# @Author : 毛鹏
import asyncio
from typing import Optional

from playwright.async_api import Locator

from src.services.ui.bases.base_data import BaseData


class PlaywrightPage:
    """页面操作"""

    def __init__(self, base_data: BaseData):
        self.base_data = base_data

    async def w_switch_tabs(self, individual: int):
        """切换页签"""
        pages = self.base_data.context.pages
        await pages[int(individual)].bring_to_front()
        self.base_data.page = pages[int(individual)]
        await asyncio.sleep(1)

    async def w_close_current_tab(self):
        """关闭当前页签"""
        await asyncio.sleep(2)
        pages = self.base_data.context.pages
        await pages[-1].close()
        self.base_data.page = pages[0]

    async def w_open_new_tab_and_switch(self, locating: Locator):
        """点击并打开新页签"""
        await locating.click()
        await asyncio.sleep(2)
        pages = self.base_data.context.pages
        new_page = pages[-1]
        await new_page.bring_to_front()
        self.base_data.page = new_page
        await asyncio.sleep(1)

    async def w_refresh(self):
        """刷新页面"""
        await self.base_data.page.reload()

    async def w_go_back(self):
        """返回上一页"""
        await self.base_data.page.go_back()

    async def w_go_forward(self):
        """前进到下一页"""
        await self.base_data.page.go_forward()
