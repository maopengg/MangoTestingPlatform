# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-29 12:11
# @Author : 毛鹏
from playwright.async_api import Locator

from auto_ui.web_base.playwright_base import PlaywrightBase


class PlaywrightInputDevice(PlaywrightBase):
    """输入设备，键盘和鼠标"""

    async def hover(self, selector):
        """鼠标悬停"""
        await self.page.hover(selector)

    async def keys(self, locator: Locator, keyboard: str):
        """按键"""
        await locator.press(keyboard)
