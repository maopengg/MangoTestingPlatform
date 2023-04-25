# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
import time

from playwright.sync_api import sync_playwright


class NewWebObj:

    def __init__(self, web_path, web_type: int = 0, headless=False):
        if web_type == 0:
            with sync_playwright() as p:
                self.web = p.chromium.launch(executable_path=web_path, headless=headless).new_page()
                self.web.goto('https://www.baidu.com')
        elif web_path == 1:
            with sync_playwright() as p:
                self.web = p.firefox.launch(executable_path=web_path, headless=headless).new_page()
        elif web_path == 2:
            with sync_playwright() as p:
                self.web = p.webkit.launch(executable_path=web_path, headless=headless).new_page()

    def __new__(cls, *args, **kwargs):
        if not hasattr(NewWebObj, 'instance'):
            cls.instance = super().__new__(cls)
        return cls.instance


if __name__ == '__main__':
    r = NewWebObj('E:\Software\Chrome\Application\chrome.exe')
    # r.web.goto('https://www.baidu.com')
    time.sleep(5)
