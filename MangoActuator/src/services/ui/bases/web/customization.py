# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-04-26 22:22
# @Author : 毛鹏
import asyncio
from typing import Optional

from playwright.async_api import Locator

from src.exceptions.error_msg import ERROR_MSG_0022
from src.exceptions.ui_exception import ElementIsEmptyError
from src.services.ui.bases.base_data import BaseData


class PlaywrightCustomization(BaseData):
    """定制开发"""

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

    async def w_click_right_coordinate(self, locating: Locator):
        """CDP定开-总和坐标点击"""
        button_position = await locating.bounding_box()
        # 计算点击位置的坐标
        x = button_position['x'] + button_position['width'] + 50
        y = button_position['y'] - 40
        await asyncio.sleep(1)
        await self.page.mouse.click(x, y)
