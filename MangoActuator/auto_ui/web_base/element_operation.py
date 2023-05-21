# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-26 22:22
# @Author : 毛鹏
import asyncio

from playwright.async_api import Locator

from auto_ui.web_base.playwright_base import PlaywrightBase


class PlaywrightElementOperation(PlaywrightBase):
    """元素操作"""

    @classmethod
    async def w_click(cls, locating: Locator):
        """元素点击"""
        await locating.click()

    @classmethod
    async def w_input(cls, locating: Locator, input_value: str):
        """元素输入"""
        await locating.fill(str(input_value))

    async def w_get_text(self, locating: Locator, set_cache_key):
        """获取元素文本"""
        value = await locating.inner_text()
        self.set(key=set_cache_key, value=value)

    async def w_click_right_coordinate(self, locating: Locator):
        """总和坐标点击"""
        button_position = await locating.bounding_box()
        # 计算点击位置的坐标
        x = button_position['x'] + button_position['width'] + 50
        y = button_position['y'] - 40
        await asyncio.sleep(1)
        await self.page.mouse.click(x, y)

    async def w_upload_files(self, locating: Locator, file_path: str):
        """点击元素上传文件"""
        with self.page.expect_file_chooser() as fc_info:
            await locating.click()
        file_chooser = fc_info.value
        file_chooser.set_files(file_path)

    async def w_drag_to(self, locating1: Locator, locating2: Locator):
        """拖动A元素到达B"""
        await locating1.drag_to(locating2)
