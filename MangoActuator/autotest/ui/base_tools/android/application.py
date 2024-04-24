# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
from autotest.ui.base_tools.base_data import BaseData


class UiautomatorApplication(BaseData):
    """应用操作"""

    def a_start_app(self, package_name: str):
        """启动应用"""
        self.android.app_start(package_name)

    def a_close_app(self, package_name: str):
        """关闭应用"""
        self.android.app_stop(package_name)

    def a_clear_app(self, package_name: str):
        """清除app数据"""
        self.android.app_clear(package_name)

    def a_app_stop_all(self):
        """停止所有app"""
        self.android.app_stop_all()

    def a_app_stop_appoint(self, package_name_list: list):
        """停止除指定app外所有app"""
        self.android.app_stop_all(excludes=package_name_list)
