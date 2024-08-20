# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
import asyncio
import json
from urllib.parse import urlparse

from playwright._impl._api_types import TimeoutError
from playwright.async_api import Locator

from src.exceptions.error_msg import ERROR_MSG_0013, ERROR_MSG_0049
from src.exceptions.ui_exception import UiTimeoutError, UrlError
from src.services.ui.base_tools.base_data import BaseData
from src.tools import InitPath


class PlaywrightBrowser(BaseData):
    """浏览器操作"""

    @classmethod
    async def w_wait_for_timeout(cls, _time: int):
        """强制等待"""
        await asyncio.sleep(int(_time))

    async def w_goto(self, url: str):
        """打开URL"""
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise UrlError(*ERROR_MSG_0049)
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

    async def w_set_cookie(self, storage_state: str):
        """设置storage_state（cookie）"""
        storage_state = json.loads(storage_state)
        await self.context.add_cookies(storage_state['cookies'])
        # 设置 local storage 和 session storage
        for storage in storage_state['origins']:
            local_storage = storage.get('localStorage', [])
            session_storage = storage.get('sessionStorage', [])
            # 设置 local storage
            for item in local_storage:
                await self.context.add_init_script(f"window.localStorage.setItem('{item['name']}', '{item['value']}');")
            # 设置 session storage
            for item in session_storage:
                await self.context.add_init_script(
                    f"window.sessionStorage.setItem('{item['name']}', '{item['value']}');")
        await self.page.reload()

    async def w_get_cookie(self):
        """测试-获取storage_state保存到log目录"""
        with open(f'{InitPath.logs_dir}/storage_state.json', 'w') as file:
            file.write(json.dumps(await self.context.storage_state()))
