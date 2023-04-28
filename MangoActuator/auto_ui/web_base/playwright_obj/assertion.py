# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-26 22:25
# @Author : 毛鹏


from playwright.async_api import Page
from .page_base import WebObj


class Assertion:
    """
    页面断言
    """

    web: Page = None
