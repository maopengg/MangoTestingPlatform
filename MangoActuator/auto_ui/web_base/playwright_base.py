# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏

from playwright.async_api import async_playwright, Page


class PlaywrightBase:
    def __init__(self, page: Page):
        self.page = page


async def new_chromium(web_path: str, headless=False) -> Page:
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False if headless is False else True,
                                               executable_path=web_path)

    return await browser.new_page()


async def new_firefox(web_path: str, headless=False) -> Page:
    playwright = await async_playwright().start()
    browser = await playwright.firefox.launch(headless=False if headless is False else True,
                                              executable_path=web_path)

    return await browser.new_page()


async def new_webkit(web_path: str, headless=False) -> Page:
    playwright = await async_playwright().start()
    browser = await playwright.webkit.launch(headless=False if headless is False else True,
                                             executable_path=web_path)

    return await browser.new_page()


if __name__ == '__main__':
    path = r'C:\Program Files\1Google\Chrome\Application\chrome.exe'
