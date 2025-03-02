# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-01-06 18:32
# @Author : 毛鹏

from playwright.sync_api import sync_playwright


def run() -> None:
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch()
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.baidu.com/")
    print(page.title())
    # ---------------------
    context.close()
    browser.close()


run()
