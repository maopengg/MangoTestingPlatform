# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
from typing import Optional

from playwright.async_api import async_playwright, Page, BrowserContext


class PlaywrightBase:

    def __init__(self):
        self.page: Optional[Page] = None
        self.context: Optional[BrowserContext] = None

    async def new_chromium(self, web_path: str, headless=False):
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False if headless is False else True,
                                                   executable_path=web_path)
        self.page = await browser.new_page()

    async def new_firefox(self, web_path: str, headless=False):
        playwright = await async_playwright().start()
        browser = await playwright.firefox.launch(headless=False if headless is False else True,
                                                  executable_path=web_path)
        self.page = await browser.new_page()

    async def new_webkit(self, web_path: str, headless=False):
        playwright = await async_playwright().start()
        browser = await playwright.webkit.launch(headless=False if headless is False else True,
                                                 executable_path=web_path)
        self.page = await browser.new_page()

    async def test_new_obj(self, path):
        await self.new_chromium(path)
        await self.page.goto('https://www.baidu.com')
        await self.page.wait_for_timeout(1000)
        await self.page.close()


if __name__ == '__main__':
    r = PlaywrightBase()
    path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(r.test_new_obj(path))
    # asyncio.run()
