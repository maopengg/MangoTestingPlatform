# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
from uiautomator2 import UiObject

from autotest.ui.base_tools.base_data import BaseData
from exceptions.ui_exception import ElementNotFoundError, ElementNotDisappearError
from tools.message.error_msg import ERROR_MSG_0043, ERROR_MSG_0044


class UiautomatorElement(BaseData):
    """元素操作"""

    @classmethod
    def a_click(cls, locating: UiObject):
        """单击"""
        locating.click()

    @classmethod
    def a_double_click(cls, locating: UiObject):
        """双击"""
        locating.center()

    @classmethod
    def a_long_click_coord(cls, locating: UiObject, time_):
        """长按元素"""
        locating.long_click(duration=time_)

    def a_input(self, locating: UiObject, text):
        """输入"""
        locating.click()
        self.android.set_fastinput_ime(True)
        self.android.send_keys(text)

    def a_get_text(self, locating: UiObject, set_cache_key=None):
        """获取元素文本"""
        value = locating.get_text()
        if set_cache_key:
            self.data_processor.set_cache(key=set_cache_key, value=value)
        return value

    def a_click_coord(self, x, y):
        """单击坐标"""
        self.android.click(x, y)

    def a_double_click_coord(self, x, y):
        """双击坐标"""
        self.android.double_click(x, y)

    @classmethod
    def a_clear_text(cls, locating: UiObject):
        """清空输入框"""
        locating.clear_text()

    @classmethod
    def a_pinch_in(cls, element: UiObject):
        """缩小"""
        element.pinch_in()

    @classmethod
    def a_pinch_out(cls, element: UiObject):
        """放大"""
        element.pinch_out()

    @classmethod
    def a_wait(cls, element: UiObject, time_):
        """等待元素出现"""
        if not element.wait(timeout=time_):
            raise ElementNotFoundError(*ERROR_MSG_0043)

    @classmethod
    def a_wait_gone(cls, element: UiObject, time_):
        """等待元素消失"""
        if not element.wait_gone(timeout=time_):
            raise ElementNotDisappearError(*ERROR_MSG_0044)

    @classmethod
    def a_drag_to_ele(cls, start_element: UiObject, end_element: UiObject):
        """拖动A元素到达B元素上"""
        start_element.drag_to(end_element)

    @classmethod
    def a_drag_to_coord(cls, element: UiObject, x, y):
        """拖动元素到坐标上"""
        element.drag_to(x, y)

    @classmethod
    def a_swipe_ele(cls, element: UiObject, direction):
        """元素内滑动"""
        element.swipe(direction)

    @classmethod
    def a_get_ele_text(cls, element: UiObject):
        """提取元素文本"""
        return element.get_text()

    @classmethod
    def a_get_ele_center(cls, element: UiObject):
        """提取元素位置"""
        x, y = element.center()
        return x, y

    @classmethod
    def a_get_ele_x(cls, element: UiObject):
        """提取元素X Y坐标"""
        x, y = element.center()
        return x, y
