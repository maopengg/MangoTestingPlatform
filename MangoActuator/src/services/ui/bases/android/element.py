# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
import traceback

import time
from uiautomator2 import UiObject
from uiautomator2.xpath import XPathSelector

from src.exceptions import UiError, ERROR_MSG_0043, ERROR_MSG_0044
from src.services.ui.bases.base_data import BaseData
from src.tools.log_collector import log


class UiautomatorElement(BaseData):
    """元素操作"""

    @classmethod
    def a_click(cls, locating: UiObject | XPathSelector):
        """元素单击"""
        try:
            locating.click()
        except Exception as error:
            traceback.print_exc()
            log.error(str(error))

    @classmethod
    def a_double_click(cls, locating: UiObject):
        """元素双击"""
        locating.click()

    def a_input(self, locating: UiObject, text):
        """单击输入"""
        locating.click()
        self.android.set_fastinput_ime(True)
        time.sleep(1)
        self.android.send_keys(text)

    @classmethod
    def a_set_text(cls, locating: UiObject, text):
        """设置文本"""
        locating.set_text(text)

    def a_click_coord(self, x, y):
        """坐标单击"""
        self.android.click(x, y)

    def a_double_click_coord(self, x, y):
        """坐标双击"""
        self.android.double_click(x, y)

    @classmethod
    def a_long_click(cls, locating: UiObject, time_):
        """长按元素"""
        locating.long_click(duration=time_)

    @classmethod
    def a_clear_text(cls, locating: UiObject):
        """清空输入框"""
        locating.clear_text()

    def a_get_text(self, locating: UiObject, set_cache_key=None):
        """获取元素文本"""
        value = locating.get_text()
        if set_cache_key:
            self.test_case.set_cache(key=set_cache_key, value=value)
        return value

    @classmethod
    def a_element_screenshot(cls, locating: UiObject, path: str):
        """元素截图"""
        im = locating.screenshot()
        im.save(path)

    @classmethod
    def a_pinch_in(cls, locating: UiObject):
        """元素缩小"""
        locating.pinch_in()

    @classmethod
    def a_pinch_out(cls, locating: UiObject):
        """元素放大"""
        locating.pinch_out()

    @classmethod
    def a_wait(cls, locating: UiObject, time_):
        """等待元素出现"""
        if not locating.wait(timeout=time_):
            raise UiError(*ERROR_MSG_0043)

    @classmethod
    def a_wait_gone(cls, locating: UiObject, time_):
        """等待元素消失"""
        if not locating.wait_gone(timeout=time_):
            raise UiError(*ERROR_MSG_0044)

    @classmethod
    def a_drag_to_ele(cls, locating: UiObject, locating2: UiObject):
        """拖动A元素到达B元素上"""
        locating.drag_to(locating2)

    @classmethod
    def a_drag_to_coord(cls, locating: UiObject, x, y):
        """拖动元素到坐标上"""
        locating.drag_to(x, y)

    @classmethod
    def a_swipe_right(cls, locating: UiObject):
        """元素内向右滑动"""
        locating.swipe('right')

    @classmethod
    def a_swipe_left(cls, locating: UiObject):
        """元素内向左滑动"""
        locating.swipe('left')

    @classmethod
    def a_swipe_up(cls, locating: UiObject):
        """元素内向上滑动"""
        locating.swipe('up')

    @classmethod
    def a_swipe_ele(cls, locating: UiObject):
        """元素内向下滑动"""
        locating.swipe('down')

    def a_get_center(self, locating: UiObject, x_key, y_key):
        """提取元素坐标"""
        x, y = locating.center()
        if x_key and y_key:
            self.test_case.set_cache(key=x_key, value=x)
            self.test_case.set_cache(key=y_key, value=y)
        return x, y
