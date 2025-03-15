# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-04-29 12:11
# @Author : 毛鹏
import asyncio
from typing import Optional

from playwright.async_api import Locator

from src.services.ui.bases.base_data import BaseData


class PlaywrightDeviceInput:
    """输入设备操作"""

    def __init__(self, base_data: BaseData):
        self.base_data = base_data

    @classmethod
    async def w_hover(cls, locating: Locator):
        """鼠标悬停"""
        await locating.hover()
        await asyncio.sleep(1)

    async def w_wheel(self, y):
        """鼠标上下滚动像素，负数代表向上"""
        await self.base_data.page.mouse.wheel(0, y)

    async def w_mouse_click(self, x: float, y: float):
        """鼠标点击坐标"""
        await self.base_data.page.mouse.click(x, y)

    async def w_mouse_center(self):
        """移动鼠标到浏览器中间"""

        viewport_size = await self.base_data.page.evaluate('''() => {
            return {
                width: window.innerWidth,
                height: window.innerHeight
            }
        }''')
        center_x = viewport_size['width'] / 2
        center_y = viewport_size['height'] / 2
        await self.base_data.page.mouse.move(center_x, center_y)

    async def w_keyboard_type_text(self, text: str):
        """模拟输入文字"""
        await self.base_data.page.keyboard.type(text)

    async def w_keyboard_insert_text(self, text: str):
        """直接输入文字"""
        await self.base_data.page.keyboard.insert_text(text)

    async def w_keys(self, keyboard: str):
        """模拟按下指定的键"""
        await self.base_data.page.keyboard.press(keyboard)

    async def w_keyboard_delete_text(self, count: int):
        """删除光标左侧的字符"""
        for _ in range(0, int(count) + 1):
            await self.base_data.page.keyboard.press("Backspace")
