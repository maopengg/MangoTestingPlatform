# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-04-26 22:22
# @Author : 毛鹏
import asyncio
from typing import Optional

import time
from playwright._impl._api_types import Error
from playwright.async_api import Locator

from autotest.ui.driver.base_data import BaseData
from exceptions.ui_exception import UploadElementInputError, ElementIsEmptyError
from tools.message.error_msg import ERROR_MSG_0022, ERROR_MSG_0024


class PlaywrightElementOperation(BaseData):
    """元素操作"""

    @classmethod
    async def w_click(cls, locating: Locator):
        """元素点击"""
        await locating.click()

    @classmethod
    async def w_input(cls, locating: Locator, input_value: str):
        """元素输入"""
        await locating.fill(str(input_value))

    async def w_list_input(self, locating: list[Locator], input_list_value: list[str], element_loc: str):
        """DESK定开-列表输入"""

        async def find_ele(page) -> Locator:
            return page.locator(f'xpath={element_loc}')

        for loc, data in zip(locating, input_list_value):
            await loc.click()
            locator: Optional[Locator] = None
            for i in self.page.frames:
                locator = await find_ele(i)
                if await locator.count() > 0:
                    break
            if locator is None:
                raise ElementIsEmptyError(*ERROR_MSG_0022)
            await locator.fill(str(data))

    async def w_get_text(self, locating: Locator, set_cache_key=None):
        """获取元素文本"""
        value = await locating.inner_text()
        if set_cache_key:
            self.data_processor.set_cache(key=set_cache_key, value=value)
        return value

    async def w_click_right_coordinate(self, locating: Locator):
        """CDP定开-总和坐标点击"""
        button_position = await locating.bounding_box()
        # 计算点击位置的坐标
        x = button_position['x'] + button_position['width'] + 50
        y = button_position['y'] - 40
        await asyncio.sleep(1)
        await self.page.mouse.click(x, y)

    async def w_upload_files(self, locating: Locator, file_path: str | list):
        """点击元素上传文件"""
        try:
            if isinstance(file_path, str):
                await locating.set_input_files(file_path)
            else:
                for file in file_path:
                    await locating.set_input_files(file)
        except Error:
            raise UploadElementInputError(*ERROR_MSG_0024)
        # with self.page.expect_file_chooser() as fc_info:
        #     await locating.click()
        # file_chooser = fc_info.value
        # file_chooser.set_files(file_path)

    async def w_drag_to(self, locating1: Locator, locating2: Locator):
        """拖动A元素到达B"""
        await locating1.drag_to(locating2)

    @classmethod
    async def w_time_click(cls, locating: Locator, _time: int):
        """循环点击指定的时间"""
        s = time.time()
        while True:
            await locating.click()
            if time.time() - s > int(_time):
                return
