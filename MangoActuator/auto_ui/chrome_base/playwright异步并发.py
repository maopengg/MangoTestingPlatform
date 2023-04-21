# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/4/21 10:54
# @Author : 毛鹏
import asyncio

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto('https://www.baidu.com')
        print(await page.title())
        await browser.close()


asyncio.run(main())
