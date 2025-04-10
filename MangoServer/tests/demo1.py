# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-03-25 22:22
# @Author : 毛鹏

if __name__ == '__main__':
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        context = browser.new_context()
        page = context.new_page()
        page.goto('https://www.baidu.com/')
        title = page.title()
        browser.close()
    print(title)