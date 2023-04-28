# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
from playwright.sync_api import Page


class PageOperation:
    """
    页面操作类
    """

    def __init__(self, web_obj: Page = None):
        self.web = web_obj

    def goto(self, url: str):
        """
        打开url
        @param url: 打开的指定url
        @return:
        """
        self.web.goto(url)


if __name__ == '__main__':
    from auto_ui.web_base.playwright_obj.new_obj import NewChromium

    path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    r = NewChromium(path)
    PageOperation.web = r.page
    PageOperation.goto('https://www.baidu.com')
    # e = PageOperation(r.page)
    # e.window_max()
