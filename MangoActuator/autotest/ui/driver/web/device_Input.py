# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-04-29 12:11
# @Author : 毛鹏
import asyncio

from playwright.async_api import Locator

from autotest.ui.driver.base_data import BaseData


class PlaywrightDeviceInput(BaseData):
    """输入设备操作"""

    async def w_hover(self, locating: Locator):
        """鼠标悬停"""
        await locating.hover()
        await asyncio.sleep(1)

    async def w_wheel(self, y):
        """鼠标上下滚动像素，负数代表向上"""
        await self.page.mouse.wheel(0, y)

    async def w_keys(self, keyboard: str):
        """按键"""
        await self.page.keyboard.press(keyboard)

    async def w_mouse_center(self):
        """移动鼠标到浏览器中间"""

        viewport_size = await self.page.evaluate('''() => {
            return {
                width: window.innerWidth,
                height: window.innerHeight
            }
        }''')
        center_x = viewport_size['width'] / 2
        center_y = viewport_size['height'] / 2
        # 移动鼠标到浏览器中心点
        await self.page.mouse.move(center_x, center_y)
