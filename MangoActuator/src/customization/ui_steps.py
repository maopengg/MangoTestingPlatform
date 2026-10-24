# -*- coding: utf-8 -*-
from mangoautomation.tools import async_method_callback, func_info, inject_to_class
from mangoautomation.uidrives import AsyncWebCustomization
from mangotools.models import MethodModel
from playwright.async_api import Locator


@inject_to_class(AsyncWebCustomization)
@async_method_callback('web', '定制开发', 'xx项目自定义方法', 1, [
    MethodModel(f='locating'),
    MethodModel(n='输入你期望的名称', f='input_value', p='请输入输入内容', d=True),
])
async def w_demo(self, locating, input_value: str):
    """xx项目自定义方法"""
    pass


@inject_to_class(AsyncWebCustomization)
@async_method_callback('web', '定制开发', '元素在页面则点击', 2, [
    MethodModel(f='locating'),
])
async def w_is_click(self, locating: Locator):
    """元素在页面则点击"""
    if await locating.count() >= 1:
        await locating.click()
