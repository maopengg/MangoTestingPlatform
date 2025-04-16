# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-01-06 18:32
# @Author : 毛鹏

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        for i in range(3):
            browser = p.chromium.connect("ws://172.22.20.1:1080")  # IPv6 连接
            context = browser.new_context()
            page = context.new_page()
            page.goto('https://www.baidu.com/')
            print(page.title())
            page.close()
            context.close()
            browser.close()
