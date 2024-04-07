# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-07-15 11:57
# @Author : 毛鹏

from playwright.async_api import Page, BrowserContext

from autotest.ui.driver.android import AndroidDriver
from autotest.ui.driver.ios import IOSDriver
from autotest.ui.driver.pc import PCDriver
from autotest.ui.driver.web import WebDevice
from autotest.ui.driver.web.new_browser import NewBrowser
from models.socket_model.ui_model import WEBConfigModel


class DriveSet(WebDevice):
    pass


class NewDriverObject(NewBrowser):

    def __init__(self, web_config: WEBConfigModel = None):
        super().__init__(web_config)
        self.browser = None
        self.web_config = web_config

    async def new_web_page(self) -> tuple[BrowserContext, Page]:
        if self.web_config is None:
            raise Exception('实例化对象错误')
        if self.browser is None:
            self.browser = await self.new_browser()
        context = await self.new_context(self.browser)
        page = await self.new_page(context)
        return context, page

    async def close(self):
        if self.browser:
            await self.browser.close()


async def test_main():
    r = NewDriverObject(web_config=WEBConfigModel(**{
        "browser_type": 0,
        "browser_port": "9222",
        "browser_path": None,
        "is_headless": 0,
        "is_header_intercept": False,
        "host": "https://app-test.growknows.cn/",
        "project_id": None
    }))
    for i in range(10):
        context1, page1 = await r.new_web_page()
        await page1.goto('https://www.baidu.com/')
        print(f'第{i}几')


if __name__ == '__main__':
    import asyncio

    asyncio.run(test_main())
