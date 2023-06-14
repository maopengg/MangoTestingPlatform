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
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False if headless is False else True,
                                                       executable_path=web_path)
            self.context = await browser.new_context()
            self.page = await self.context.new_page()

    async def new_firefox(self, web_path: str, headless=False):
        async with async_playwright() as playwright:
            browser = await playwright.firefox.launch(headless=False if headless is False else True,
                                                      executable_path=web_path)
            self.context = await browser.new_context()
            self.page = await self.context.new_page()

    async def new_webkit(self, web_path: str, headless=False):
        async with async_playwright() as playwright:
            browser = await playwright.webkit.launch(headless=False if headless is False else True,
                                                     executable_path=web_path)
            self.context = await browser.new_context()
            self.page = await self.context.new_page()


if __name__ == '__main__':
    r = PlaywrightBase()
    path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    import asyncio

    asyncio.run(r.new_chromium(path))
