# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
from playwright.sync_api import Page


class PlaywrightPageOperation:
    """页面操作类"""

    def __init__(self, page: Page = None):
        self.page = page

    def goto(self, url: str):
        """
        打开url
        @param url: 打开的指定url
        @return:
        """
        self.page.goto(url, timeout=50000)

    def screenshot(self, path: str, full_page=True):
        """整个页面截图"""
        self.page.screenshot(path=path, full_page=full_page)

    def ele_screenshot(self, selector: str, path: str):
        """元素截图"""
        self.page.locator(selector).screenshot(path=path)


if __name__ == '__main__':
    from auto_ui.web_base.playwright_obj.new_obj import NewChromium

    path1 = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    r = NewChromium(path1)
    # PageOperation.web = r.page
    # PageOperation.goto('https://www.baidu.com')
    # e = PageOperation(r.page)
    # e.window_max()
