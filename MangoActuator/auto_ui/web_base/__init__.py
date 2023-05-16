# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/5/16 14:50
# @Author : 毛鹏
from auto_ui.web_base.assertion import PlaywrightAssertion
from auto_ui.web_base.element_operation import PlaywrightElementOperation
from auto_ui.web_base.input_device import PlaywrightInputDevice
from auto_ui.web_base.operation_browser import PlaywrightOperationBrowser
from auto_ui.web_base.operation_page import PlaywrightPageOperation


class WebDevice(PlaywrightPageOperation,
                PlaywrightAssertion,
                PlaywrightOperationBrowser,
                PlaywrightElementOperation,
                PlaywrightInputDevice):
    pass
