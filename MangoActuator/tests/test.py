# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-01-06 18:32
# @Author : 毛鹏
import asyncio

from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect("ws://172.21.222.119:3000/")
        page_list = []
        for _ in range(100):
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto('https://www.baidu.com/')
            print(await page.title())
        await browser.close()


with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()
    page = context.new_page()
    page.goto('https://www.baidu.com/')
    title = page.title()
    print(title)
    browser.close()
