# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-29 12:11
# @Author : 毛鹏
import asyncio

from playwright.async_api import Locator

from auto_ui.web_base.playwright_base import PlaywrightBase


class PlaywrightInputDevice(PlaywrightBase):
    """输入设备操作"""

    async def w_hover(self, locating: Locator):
        """鼠标悬停"""
        await locating.hover()
        await asyncio.sleep(1)

    async def w_wheel(self, y):
        """鼠标上下滚动像素，负数代表向上"""
        await self.page.mouse.wheel(0, y)

    async def w_keys(self, locating: Locator, keyboard: str):
        """按键"""
        await locating.press(keyboard)
