# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
from autotest.ui.driver.android.android_base import AndroidBase


class UiautomatorEquipmentDevice(AndroidBase):
    """设备操作"""

    def a_screen_on(self):
        """打开屏幕"""
        self.android.screen_on()
        self.a_sleep(1)

    def a_screen_off(self):
        """关闭屏幕"""
        self.android.screen_off()
        self.a_sleep(1)

    def a_swipe_left(self):
        """获取屏幕开关状态"""
        self.android.info.get('screenOn')

    def a_home(self):
        """返回首页"""
        self.android.keyevent("home")

    def a_back(self):
        """返回一步"""
        self.android.keyevent("back")

    def a_get_window_size(self):
        """提取屏幕尺寸"""
        w, h = self.android.window_size()
        return w, h

    def a_push(self, feli_path, catalogue):
        """推送一个文件-未测试"""
        self.android.push(feli_path, catalogue)

    def a_pull(self, feli_path, catalogue):
        """提取文件-未测试"""
        self.android.pull(feli_path, catalogue)

    def a_unlock(self):
        """解锁屏幕-未测试"""
        self.android.unlock()
        self.press_home()

    def a_press_home(self):
        """按home键"""
        self.android.press('home')

    def a_press_back(self):
        """按back键"""
        self.android.press('back')

    def a_press_left(self):
        """按left键"""
        self.android.press('left')

    def a_press_right(self):
        """按right键"""
        self.android.press('right')

    def a_press_up(self):
        """按up键"""
        self.android.press('up')

    def a_press_down(self):
        """按down键"""
        self.android.press('down')

    def a_press_center(self):
        """按center键"""
        self.android.press('center')

    def a_press_menu(self):
        """按menu键"""
        self.android.press('menu')

    def a_press_search(self):
        """按search键"""
        self.android.press('search')

    def a_press_enter(self):
        """按enter键"""
        self.android.press('enter')

    def a_press_delete(self):
        """按delete键"""
        self.android.press('delete')

    def a_press_recent(self):
        """按recent键"""
        self.android.press('recent')

    def a_press_volume_up(self):
        """按volume_up键"""
        self.android.press('volume_up')

    def a_press_volume_down(self):
        """按volume_down键"""
        self.android.press('volume_down')

    def a_press_volume_mute(self):
        """按volume_mute键"""
        self.android.press('volume_mute')

    def a_press_camera(self):
        """按camera键"""
        self.android.press('camera')

    def a_press_power(self):
        """按power键"""
        self.android.press('power')
