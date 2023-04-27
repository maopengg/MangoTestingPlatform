# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-25 22:33
# @Author : 毛鹏
from playwright.sync_api import sync_playwright


class NewChromium:

    def __init__(self, web_path: str, headless=False):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False if headless is False else True,
                                                       channel='chrome',
                                                       args=['--window-position=-5,-5'],
                                                       executable_path=web_path)

        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1080})
        self.page = self.context.new_page()

    def close(self):
        self.browser.close()


class NewFirefox:

    def __init__(self, web_path: str, headless=False):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.firefox.launch(headless=False if headless is False else True,
                                                      channel='firefox',
                                                      args=['--window-position=-5,-5'],
                                                      executable_path=web_path)
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1080})
        self.page = self.context.new_page()

    def close(self):
        self.browser.close()


class NewWebkit:

    def __init__(self, web_path: str, headless=False):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.webkit.launch(headless=False if headless is False else True,
                                                     channel='webkit',
                                                     args=['--window-position=-5,-5'],
                                                     executable_path=web_path)
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1080})
        self.page = self.context.new_page()

    def close(self):
        self.browser.close()


if __name__ == '__main__':
    path = r'E:\Software\Chrome\Application\chrome.exe'
    r = NewChromium(path)
    r.navigate('https://www.baidu.com')
