# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
from playwright.sync_api import Page, Locator


class PageOperation:
    """
    页面操作类
    """
    web: Page = None

    @classmethod
    def goto(cls, url: str):
        """
        打开url
        @param url: 打开的指定url
        @return:
        """
        cls.web.goto(url)


if __name__ == '__main__':
    from auto_ui.web_base.playwright_obj.new_obj import NewChromium

    path = r'E:\Software\Chrome\Application\chrome.exe'
    r = NewChromium(path)
    # e = PageOperation(r.page)
    # e.window_max()
