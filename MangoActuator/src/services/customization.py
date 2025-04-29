# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-04-29 14:06
# @Author : 毛鹏
from mangokit.decorator import inject_to_class, async_method_callback, func_info
from mangokit.models import MethodModel
from mangokit.uidrive.web.async_web import AsyncWebCustomization

"""
示例，自定义方法

规则：
1.必须使用：@inject_to_class(AsyncWebCustomization)
2.必须使用：async_method_callback装饰。参考如下，type可以输入：web， android， web_ass, android_ass
3.函数必须写注释，方法如下。不可以加回车和空格
4.写完了点击发送缓存数据按钮
"""


@inject_to_class(AsyncWebCustomization)
@async_method_callback('web', '定制开发', 3, [
    MethodModel(f='locating'),
    MethodModel(f='input_value', p='请输入输入内容', d=True)])
async def w_demo(self, locating, input_value: str):
    """xx项目自定义方法"""
    pass
