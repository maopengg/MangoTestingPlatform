# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-04-25 22:33
# @Author : 毛鹏
import asyncio
import json
from urllib.parse import urlparse

from playwright._impl._errors import TimeoutError, Error
from playwright.async_api import Locator

from src.exceptions import UiError, ERROR_MSG_0013, ERROR_MSG_0049, ERROR_MSG_0058
from src.services.ui.bases.base_data import BaseData
from src.tools import project_dir


class PlaywrightBrowser:
    """浏览器操作"""

    def __init__(self, base_data: BaseData):
        self.base_data = base_data

    @classmethod
    async def w_wait_for_timeout(cls, _time: int):
        """强制等待"""
        await asyncio.sleep(int(_time))

    async def w_goto(self, url: str):
        """打开URL"""
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise UiError(*ERROR_MSG_0049)
            await self.base_data.page.goto(url, timeout=60000)
            await asyncio.sleep(2)
        except TimeoutError:
            raise UiError(*ERROR_MSG_0013, value=(url,))
        except Error:
            raise UiError(*ERROR_MSG_0058, value=(url,))

    async def w_screenshot(self, path: str, full_page=True):
        """整个页面截图"""
        await self.base_data.page.screenshot(path=path, full_page=full_page)

    @classmethod
    async def w_ele_screenshot(cls, locating: Locator, path: str):
        """元素截图"""
        await locating.screenshot(path=path)

    async def w_alert(self):
        """设置弹窗不予处理"""
        self.base_data.page.on("dialog", lambda dialog: dialog.accept())

    async def w_get_cookie(self):
        """获取storage_state保存到download目录"""
        with open(f'{project_dir.download()}/storage_state.json', 'w') as file:
            file.write(json.dumps(await self.base_data.context.storage_state()))

    async def w_set_cookie(self, storage_state: str):
        """设置storage_state（cookie）"""
        storage_state = json.loads(storage_state)
        await self.base_data.context.add_cookies(storage_state['cookies'])
        for storage in storage_state['origins']:
            local_storage = storage.get('localStorage', [])
            session_storage = storage.get('sessionStorage', [])
            for item in local_storage:
                await self.base_data.context.add_init_script(
                    f"window.localStorage.setItem('{item['name']}', '{item['value']}');")
            for item in session_storage:
                await self.base_data.context.add_init_script(
                    f"window.sessionStorage.setItem('{item['name']}', '{item['value']}');")
        await self.base_data.page.reload()

    async def w_clear_cookies(self):
        """清除所有cookies"""
        await self.base_data.context.clear_cookies()

    async def w_clear_storage(self):
        """清除本地存储和会话存储"""
        await self.base_data.page.evaluate("() => localStorage.clear()")
        await self.base_data.page.evaluate("() => sessionStorage.clear()")
