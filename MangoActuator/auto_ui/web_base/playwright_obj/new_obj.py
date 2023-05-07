# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
import asyncio
import time
from playwright.async_api import async_playwright, Page


async def new_chromium(web_path: str, headless=False) -> Page:
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False if headless is False else True,
                                               executable_path=web_path)

    page = await browser.new_page()
    return page


async def new_firefox(web_path: str, headless=False) -> Page:
    playwright = await async_playwright().start()
    browser = await playwright.firefox.launch(headless=False if headless is False else True,
                                              channel='chrome',
                                              args=['--window-position=-5,-5'],
                                              executable_path=web_path)

    page = await browser.new_page()
    return page


async def new_webkit(web_path: str, headless=False) -> Page:
    playwright = await async_playwright().start()
    browser = await playwright.webkit.launch(headless=False if headless is False else True,
                                             channel='chrome',
                                             args=['--window-position=-5,-5'],
                                             executable_path=web_path)

    page = await browser.new_page()
    return page


if __name__ == '__main__':
    path = r'C:\Program Files\1Google\Chrome\Application\chrome.exe'


    async def hh():
        p = await new_chromium(path)
        await p.goto('https://www.baidu.com')


    loop = asyncio.new_event_loop()  # 创建新的事件循环
    asyncio.set_event_loop(loop)  # 设置新的事件循环为当前事件循环
    p = loop.run_until_complete(hh())  # 运行事件循环
    time.sleep(4)
    # def hhh():
    #     page = await new_chromium(path)
    #     page.goto('https://www.baidu.com')