# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
from playwright.async_api import async_playwright, Page, BrowserContext

from utils.test_data_cache.data_cleaning import DataCleaning


class PlaywrightBase(DataCleaning):

    def __init__(self, page: Page, context: BrowserContext = None):
        super().__init__()
        self.page = page
        self.context = context


async def new_chromium(web_path: str, headless=False) -> Page:
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False if headless is False else True,
                                               executable_path=web_path)
    context = await browser.new_context()
    return await context.new_page()


# 不同的上下文
# async def run(playwright):
#     # create a chromium browser instance
#     chromium = playwright.chromium
#     browser = await chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
#                                     headless=False)
#
#     # create two isolated browser contexts
#     user_context = await browser.new_context()
#     admin_context = await browser.new_context()
#     a = await user_context.new_page()
#     await a.goto('https://www.baidu.com')
#     # create pages and interact with contexts independently
#     b = await admin_context.new_page()
#     await b.goto('https://pandapy.com/')
#     await asyncio.sleep(5)
#
#
# async def main():
#     async with async_playwright() as playwright:
#         await run(playwright)
#
#
# asyncio.run(main())

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
