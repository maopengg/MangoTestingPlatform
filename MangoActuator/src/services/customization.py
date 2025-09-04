# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-04-29 14:06
# @Author : 毛鹏
from mangoautomation.uidrive.web.async_web import AsyncWebCustomization
from mangotools.decorator import *
from mangotools.models import MethodModel
from playwright.async_api import Locator

"""
示例，自定义方法

规则：
1.必须使用：@inject_to_class(AsyncWebCustomization)
2.必须使用：async_method_callback装饰。参考如下，type可以输入：web， android， web_ass, android_ass
3.函数必须写注释，方法如下。不可以加回车和空格
"""


@inject_to_class(AsyncWebCustomization)
@async_method_callback('web', '定制开发', 1, [
    MethodModel(f='locating'),
    MethodModel(n='输入你期望的名称', f='input_value', p='请输入输入内容', d=True)])
async def w_demo(self, locating, input_value: str):
    """xx项目自定义方法"""
    pass


@inject_to_class(AsyncWebCustomization)
@async_method_callback('web', '定制开发', 2, [
    MethodModel(f='locating')])
async def w_is_click(self, locating: Locator):
    """元素在页面则点击"""
    if await locating.count() >= 1:
        await locating.click()
