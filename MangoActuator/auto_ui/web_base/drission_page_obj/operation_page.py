# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
from playwright.sync_api import Page


class OperationPage:

    def __init__(self, web_obj: Page):
        self.web = web_obj

    def window_max(self):
        self.web.goto('https://www.baidu.com')


if __name__ == '__main__':
    from auto_ui.web_base.playwright_obj.new_obj import BasePage
    path = r'E:\Software\Chrome\Application\chrome.exe'
    r = BasePage(path)
    e = PageOpe(r.page)
    e.window_max()