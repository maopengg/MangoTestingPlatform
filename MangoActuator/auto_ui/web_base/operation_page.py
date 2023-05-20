# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
import asyncio

from auto_ui.web_base.playwright_base import PlaywrightBase


class PlaywrightPageOperation(PlaywrightBase):
    """浏览器操作类"""

    async def w_switch_tabs(self, individual: int):
        """切换页签"""
        pages = self.context.pages
        await pages[individual].bring_to_front()
        await asyncio.sleep(1)
