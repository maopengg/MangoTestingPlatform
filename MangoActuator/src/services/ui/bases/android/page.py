# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023/4/6 13:31
# @Author : 毛鹏

from uiautomator2 import Direction

from src.services.ui.bases.base_data import BaseData


class UiautomatorPage(BaseData):
    """页面操作"""

    def a_swipe_right(self):
        """右滑"""
        self.android.swipe_ext(Direction.HORIZ_FORWARD)

    def a_swipe_left(self):
        """左滑"""
        self.android.swipe_ext(Direction.HORIZ_BACKWARD)

    def a_swipe_up(self):
        """上滑"""
        self.android.swipe_ext(Direction.FORWARD)

    def a_swipe_down(self):
        """下滑"""
        self.android.swipe_ext(Direction.BACKWARD)

    def a_swipe(self, sx, sy, ex, ey):
        """坐标滑动"""
        self.android.swipe(sx, sy, ex, ey, 0.5)

    def a_drag(self, sx, sy, ex, ey):
        """坐标拖动"""
        self.android.drag(sx, sy, ex, ey, 0.5)

    def a_open_notification(self):
        """打开通知"""
        self.android.open_notification()

    def a_open_quick_settings(self):
        """打开快速通知"""
        self.android.open_quick_settings()

    def a_screenshot(self, filepath: str):
        """屏幕截图"""
        self.android.screenshot(filename=filepath)

    def a_long_click(self, x, y, time_=3):
        """长按屏幕3秒"""
        self.android.long_click(x, y, time_)

    def a_set_orientation_natural(self):
        """设置为natural"""
        self.android.set_orientation("natural")

    def a_set_orientation_left(self):
        """设置为natural"""
        self.android.set_orientation("left")

    def a_set_orientation_right(self):
        """设置为right"""
        self.android.set_orientation("right")

    def a_set_orientation_upsidedown(self):
        """设置为upsidedown"""
        self.android.set_orientation("upsidedown")

    def a_freeze_rotation(self):
        """冻结旋转"""
        self.android.freeze_rotation()

    def a_freeze_rotation_false(self):
        """取消冻结旋转"""
        self.android.freeze_rotation(False)

    def a_dump_hierarchy(self):
        """获取转储的内容"""
        return self.android.dump_hierarchy()

    def a_open_notification(self):
        """打开通知"""
        return self.android.dump_hierarchy()

    def a_open_quick_settings(self):
        """打开快速设置"""
        return self.android.dump_hierarchy()
