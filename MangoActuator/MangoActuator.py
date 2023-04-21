# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-05 11:34
# @Author : 毛鹏
# import asyncio
#
from utlis.logs.nuw_logs import nuw_dir

nuw_dir()
#
# from utlis.client.client_socket import ClientWebSocket
#
# # pyinstaller -F -c .\MangoActuator.py
# print("================执行端正在启动================")
# client = ClientWebSocket()
# loop = asyncio.new_event_loop()  # 创建新的事件循环
# asyncio.set_event_loop(loop)  # 设置新的事件循环为当前事件循环
# loop.run_until_complete(client.client_run())  # 运行事件循环
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
