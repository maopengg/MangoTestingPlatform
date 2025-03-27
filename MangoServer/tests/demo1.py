# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-03-25 22:22
# @Author : 毛鹏
import asyncio

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect("ws://172.21.222.119:3000/")
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto('https://www.baidu.com/')
        print(await page.title())
        await browser.close()


asyncio.run(main())
