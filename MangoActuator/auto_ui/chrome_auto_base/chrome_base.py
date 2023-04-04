# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:28
# @Author : 毛鹏
from DrissionPage import WebPage
from DrissionPage.configs.chromium_options import ChromiumOptions


class ChromeBase(WebPage):
    """实例化对象，以及对象方法重写"""

    def __init__(self, local_port, browser_path):
        do = ChromiumOptions(read_file=False).set_paths(
            local_port=local_port,
            browser_path=browser_path)
        # do.set_argument('--remote-allow-origins=*')cls=None,
        super().__init__(driver_or_options=do, session_or_options=False)