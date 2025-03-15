# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
from time import sleep

from src.services.ui.bases.base_data import BaseData


class UiautomatorEquipment:
    """设备操作"""

    def __init__(self, base_data: BaseData):
        self.base_data = base_data

    @classmethod
    def a_sleep(cls, time_: int):
        """强制等待"""
        sleep(time_)

    def a_screen_on(self):
        """打开屏幕"""
        self.base_data.android.screen_on()
        self.a_sleep(1)

    def a_screen_off(self):
        """关闭屏幕"""
        self.base_data.android.screen_off()
        self.a_sleep(1)

    def a_swipe_left(self):
        """获取屏幕开关状态"""
        self.base_data.android.info.get('screenOn')

    #
    # def a_home(self):
    #     """返回首页"""
    #     self.android.keyevent("home")
    #
    # def a_back(self):
    #     """返回一步"""
    #     self.android.keyevent("back")

    def a_get_window_size(self):
        """提取屏幕尺寸"""
        w, h = self.base_data.android.window_size()
        return w, h

    def a_push(self, feli_path, catalogue):
        """推送一个文件-未测试"""
        self.base_data.android.push(feli_path, catalogue)

    def a_pull(self, feli_path, catalogue):
        """提取文件-未测试"""
        self.base_data.android.pull(feli_path, catalogue)

    def a_unlock(self):
        """解锁屏幕"""
        self.base_data.android.unlock()

    def a_press_home(self):
        """按home键"""
        self.base_data.android.press('home')

    def a_press_back(self):
        """按back键"""
        self.base_data.android.press('back')

    def a_press_left(self):
        """按left键"""
        self.base_data.android.press('left')

    def a_press_right(self):
        """按right键"""
        self.base_data.android.press('right')

    def a_press_up(self):
        """按up键"""
        self.base_data.android.press('up')

    def a_press_down(self):
        """按down键"""
        self.base_data.android.press('down')

    def a_press_center(self):
        """按center键"""
        self.base_data.android.press('center')

    def a_press_menu(self):
        """按menu键"""
        self.base_data.android.press('menu')

    def a_press_search(self):
        """按search键"""
        self.base_data.android.press('search')

    def a_press_enter(self):
        """按enter键"""
        self.base_data.android.press('enter')

    def a_press_delete(self):
        """按delete键"""
        self.base_data.android.press('delete')

    def a_press_recent(self):
        """按recent键"""
        self.base_data.android.press('recent')

    def a_press_volume_up(self):
        """按volume_up键"""
        self.base_data.android.press('volume_up')

    def a_press_volume_down(self):
        """按volume_down键"""
        self.base_data.android.press('volume_down')

    def a_press_volume_mute(self):
        """按volume_mute键"""
        self.base_data.android.press('volume_mute')

    def a_press_camera(self):
        """按camera键"""
        self.base_data.android.press('camera')

    def a_press_power(self):
        """按power键"""
        self.base_data.android.press('power')
