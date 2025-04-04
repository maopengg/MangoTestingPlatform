# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-04-26 22:22
# @Author : 毛鹏
import os.path
from typing import Optional

import time
from playwright.async_api import Locator, Error

from src.exceptions import *
from src.services.ui.bases.base_data import BaseData
from src.tools import project_dir


class PlaywrightElement:
    """元素操作"""

    def __init__(self, base_data: BaseData):
        self.base_data = base_data

    @classmethod
    async def w_click(cls, locating: Locator):
        """元素单击"""
        await locating.click()

    @classmethod
    async def w_dblclick(cls, locating: Locator):
        """元素双击"""
        await locating.dblclick()

    @classmethod
    async def w_force_click(cls, locating: Locator):
        """强制单击"""
        await locating.evaluate('element => element.click()')

    @classmethod
    async def w_input(cls, locating: Locator, input_value: str):
        """元素输入"""
        await locating.fill(str(input_value))

    async def w_get_text(self, locating: Locator, set_cache_key=None):
        """获取元素文本"""
        value = await locating.inner_text()
        log.debug(f'获取元素的值：{value}，存储的key：{set_cache_key}')
        if set_cache_key:
            self.base_data.test_data.set_cache(key=set_cache_key, value=value)
            self.base_data.parent.set_tips_info(f'元素key设置成功，key：{set_cache_key}，value：{value}')

        return value

    @classmethod
    async def w_upload_files(cls, locating: Locator, file_path: str | list):
        """拖拽文件上传"""
        try:
            if isinstance(file_path, str):
                await locating.set_input_files(file_path)
            else:
                for file in file_path:
                    await locating.set_input_files(file)
        except Error:
            raise UiError(*ERROR_MSG_0024)

    async def w_click_upload_files(self, locating: Locator, file_path: str | list):
        """点击并选择文件上传"""
        async with self.base_data.page.expect_file_chooser() as fc_info:
            await locating.click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(file_path)

    async def w_download(self, locating: Locator, file_key: str):
        """下载文件"""
        async with self.base_data.page.expect_download() as download_info:
            await locating.click()
        download = await download_info.value
        file_name = download.suggested_filename
        save_path = os.path.join(project_dir.download(), file_name)
        await download.save_as(save_path)
        self.base_data.test_data.set_cache(file_key, file_name)

    @classmethod
    async def w_drag_to(cls, locating1: Locator, locating2: Locator):
        """拖动A元素到达B"""
        await locating1.drag_to(locating2)

    @classmethod
    async def w_time_click(cls, locating: Locator, n: int):
        """循环点击N秒"""
        try:
            n = int(n)
        except ValueError:
            raise UiError(*ERROR_MSG_0056)
        s = time.time()
        while True:
            await locating.click()
            if time.time() - s > n:
                return

    async def w_drag_up_pixel(self, locating: Locator, n: int):
        """往上拖动N个像素"""
        try:
            n = int(n)
        except ValueError:
            raise UiError(*ERROR_MSG_0056)

        box = await locating.bounding_box()

        if box:
            await self.base_data.page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
            await self.base_data.page.mouse.down()
            await self.base_data.page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2 - n)
            await self.base_data.page.mouse.up()

    async def w_drag_down_pixel(self, locating: Locator, n: int):
        """往下拖动N个像素"""
        try:
            n = int(n)
        except ValueError:
            raise UiError(*ERROR_MSG_0056)

        box = await locating.bounding_box()

        if box:
            await self.base_data.page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
            await self.base_data.page.mouse.down()
            await self.base_data.page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2 + n)
            await self.base_data.page.mouse.up()

    async def w_drag_left_pixel(self, locating: Locator, n: int):
        """往左拖动N个像素"""
        try:
            n = int(n)
        except ValueError:
            raise UiError(*ERROR_MSG_0056)

        box = await locating.bounding_box()

        if box:
            await self.base_data.page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
            await self.base_data.page.mouse.down()
            await self.base_data.page.mouse.move(box['x'] + box['width'] / 2 - n, box['y'] + box['height'] / 2)
            await self.base_data.page.mouse.up()

    async def w_drag_right_pixel(self, locating: Locator, n: int):
        """往右拖动N个像素"""
        try:
            n = int(n)
        except ValueError:
            raise UiError(*ERROR_MSG_0056)
        box = await locating.bounding_box()

        if box:
            await self.base_data.page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
            await self.base_data.page.mouse.down()
            await self.base_data.page.mouse.move(box['x'] + box['width'] / 2 + n, box['y'] + box['height'] / 2)
            await self.base_data.page.mouse.up()
