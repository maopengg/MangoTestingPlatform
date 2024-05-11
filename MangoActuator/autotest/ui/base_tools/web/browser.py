# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
import asyncio

from playwright._impl._api_types import TimeoutError
from playwright.async_api import Locator

from autotest.ui.base_tools.base_data import BaseData
from exceptions.ui_exception import UiTimeoutError
from tools.message.error_msg import ERROR_MSG_0013


class PlaywrightBrowser(BaseData):
    """浏览器操作"""

    @classmethod
    async def w_wait_for_timeout(cls, _time: int):
        """强制等待"""
        await asyncio.sleep(int(_time))

    async def w_goto(self, url: str):
        """打开URL"""
        try:
            await self.page.goto(url, timeout=60000)
            await asyncio.sleep(2)
        except TimeoutError:
            raise UiTimeoutError(*ERROR_MSG_0013, value=(url,))

    async def w_screenshot(self, path: str, full_page=True):
        """整个页面截图"""
        await self.page.screenshot(path=path, full_page=full_page)

    @classmethod
    async def w_ele_screenshot(cls, locating: Locator, path: str):
        """元素截图"""
        await locating.screenshot(path=path)

    async def w_alert(self):
        """设置弹窗不予处理"""
        self.page.on("dialog", lambda dialog: dialog.accept())

    async def w_download(self, save_path: str):
        """下载文件"""
        async with self.page.expect_download() as download_info:
            await self.page.get_by_text("Download file").click()
        download = await download_info.value
        await download.save_as(save_path)
