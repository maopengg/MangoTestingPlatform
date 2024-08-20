# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
import time
import uiautomator2

from src.exceptions.error_msg import ERROR_MSG_0046
from src.exceptions.ui_exception import PackageNameError
from src.services.ui.base_tools.base_data import BaseData


class UiautomatorApplication(BaseData):
    """应用操作"""

    def a_start_app(self, package_name: str):
        """启动应用"""
        if not package_name:
            raise PackageNameError(*ERROR_MSG_0046)
        try:
            self.android.app_start(package_name)
            time.sleep(4)
        except uiautomator2.exceptions.BaseError:
            raise PackageNameError(*ERROR_MSG_0046)

    def a_close_app(self, package_name: str):
        """关闭应用"""
        if not package_name:
            raise PackageNameError(*ERROR_MSG_0046)
        try:
            self.android.app_stop(package_name)
        except uiautomator2.exceptions.BaseError:
            raise PackageNameError(*ERROR_MSG_0046)

    def a_clear_app(self, package_name: str):
        """清除app数据"""
        if not package_name:
            raise PackageNameError(*ERROR_MSG_0046)

        current_app = self.android.app_current()
        if current_app.get("package") == package_name:
            try:
                self.android.app_clear(package_name)
            except uiautomator2.exceptions.BaseError:
                raise PackageNameError(*ERROR_MSG_0046)

    def a_app_stop_all(self):
        """停止所有app"""
        self.android.app_stop_all()

    def a_app_stop_appoint(self, package_name_list: list):
        """停止除指定app外所有app"""
        if package_name_list:
            try:
                self.android.app_stop_all(excludes=package_name_list)
            except uiautomator2.exceptions.BaseError:
                raise PackageNameError(*ERROR_MSG_0046)
        else:
            raise PackageNameError(*ERROR_MSG_0046)
