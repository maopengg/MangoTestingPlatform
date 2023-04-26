# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
import time

from playwright.sync_api import sync_playwright
from utlis.logs.log_control import ERROR


class BasePage:

    def __init__(self, web_path: str, web_type: int = 0, headless=False):
        head = False if headless is False else True
        self.playwright = sync_playwright().start()
        match web_type:
            case 0:
                self.browser = self.playwright.chromium.launch(headless=head,
                                                               channel='chrome',
                                                               args=['--window-position=-5,-5'],
                                                               executable_path=web_path)
            case 1:
                self.browser = self.playwright.firefox.launch(headless=head,
                                                              channel='chrome',
                                                              args=['--window-position=-5,-5'],
                                                              executable_path=web_path)
            case 2:
                self.browser = self.playwright.webkit.launch(headless=head,
                                                             channel='chrome',
                                                             args=['--window-position=-5,-5'],
                                                             executable_path=web_path)
            case _:
                ERROR.logger.error(f'没有对应的浏览器类型，请检查浏览器type{web_type}')
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1080})
        self.page = self.context.new_page()

    def navigate(self, url):
        self.page.goto(url)
        time.sleep(5)

    def close(self):
        self.browser.close()


if __name__ == '__main__':
    path = r'E:\Software\Chrome\Application\chrome.exe'
    r = BasePage(path)
    r.navigate('https://www.baidu.com')
