# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-26 22:16
# @Author : 毛鹏
from auto_ui.web_base.playwright_obj.assertion import PlaywrightAssertion
from auto_ui.web_base.playwright_obj.element_operation import PlaywrightElementOperation
from auto_ui.web_base.playwright_obj.input_device import PlaywrightInputDevice
from auto_ui.web_base.playwright_obj.operation_browser import PlaywrightOperationBrowser
from auto_ui.web_base.playwright_obj.operation_page import PlaywrightPageOperation


class WebDevice(PlaywrightPageOperation,
                PlaywrightAssertion,
                PlaywrightOperationBrowser,
                PlaywrightElementOperation,
                PlaywrightInputDevice):
    pass

