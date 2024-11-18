# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
from uiautomator2 import UiObject


class UiautomatorAssertion:
    """元素断言"""

    def a_assert_ele_exists(self, locating: UiObject, assertion, expect):
        """断言元素存在"""
        pass

    def a_assert_ele_text(self, locating: UiObject, assertion, expect):
        """断言元素文本"""
        pass

    def a_assert_ele_attribute(self, locating: UiObject, attribute, assertion, expect):
        """断言元素属性"""
        pass

    def a_assert_ele_center(self, locating: UiObject, assertion, expect):
        """断言元素位置"""
        pass

    def a_assert_ele_x(self, locating: UiObject, assertion, expect):
        """断言元素X坐标"""
        pass

    def a_assert_ele_y(self, locating: UiObject, assertion, expect):
        """断言元素Y坐标"""
        pass
