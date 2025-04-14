# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-04-26 22:22
# @Author : 毛鹏

from playwright.async_api import Locator

from src.services.ui.bases.base_data import BaseData


class PlaywrightCustomization:
    """定制开发"""

    def __init__(self, base_data: BaseData):
        self.base_data = base_data

    async def web_click_and_drag_horizontally(self, locating: Locator, x: int, y: int, drag_distance: int):
        """拖动小时稳定图标滑块"""
        box = await locating.bounding_box()
        if not box:
            raise ValueError("无法获取元素边界框，元素可能不可见或不存在")
        start_x = box['x'] + float(x)
        start_y = box['y'] + float(y)
        await locating.page.mouse.move(start_x, start_y)
        await locating.page.mouse.down()
        steps = 20
        for step in range(1, steps + 1):
            x = start_x + (int(drag_distance) * step / steps)
            await locating.page.mouse.move(x, start_y)
            await locating.page.wait_for_timeout(50)  # 每步间隔50ms

        await locating.page.mouse.up()
