# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
from autotest.ui.driver.android.android_base import AndroidBase


class UiautomatorApplication(AndroidBase):
    """应用操作"""

    def a_start_app(self):
        """启动应用"""
        self.android.app_start(self.android_config.app_name)
        self.a_sleep(5)

    def a_close_app(self, app_name: str):
        """关闭应用"""
        self.android.app_stop(app_name)
        self.a_sleep(1)

    def a_clear_app(self, app_name: str):
        """清除app数据"""
        self.android.app_clear(app_name)
        self.a_sleep(1)

    def a_app_stop_all(self):
        """停止所有app"""
        self.android.app_stop_all()

    def a_app_stop_appoint(self, app_list: list):
        """停止除指定app外所有app"""
        self.android.app_stop_all(excludes=app_list)
