# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-26 22:29
# @Author : 毛鹏
from playwright.async_api import Page

from auto_ui.web_base.playwright_obj.operation_page import PageOperation
from auto_ui.web_base.playwright_obj.assertion import Assertion
from auto_ui.web_base.playwright_obj.operation_browser import OperationBrowser
from auto_ui.web_base.playwright_obj.element_operation import ElementOperation


class WebDevice(PageOperation, Assertion, OperationBrowser, ElementOperation):
    web: Page
