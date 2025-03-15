# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
import time
import uiautomator2

from src.exceptions import UiError, ERROR_MSG_0046
from src.services.ui.bases.base_data import BaseData


class UiautomatorApplication:
    """应用操作"""

    def __init__(self, base_data: BaseData):
        self.base_data = base_data

    def a_start_app(self, package_name: str):
        """启动应用"""
        if not package_name:
            raise UiError(*ERROR_MSG_0046)
        # try:
        self.base_data.android.app_start(package_name)
        time.sleep(4)
        # except uiautomator2.exceptions.BaseError:
        #     raise UiError(*ERROR_MSG_0046)

    def a_close_app(self, package_name: str):
        """关闭应用"""
        if not package_name:
            raise UiError(*ERROR_MSG_0046)
        try:
            self.base_data.android.app_stop(package_name)
        except uiautomator2.exceptions.BaseError:
            raise UiError(*ERROR_MSG_0046)

    def a_clear_app(self, package_name: str):
        """清除app数据"""
        if not package_name:
            raise UiError(*ERROR_MSG_0046)

        current_app = self.base_data.android.app_current()
        if current_app.get("package") == package_name:
            try:
                self.base_data.android.app_clear(package_name)
            except uiautomator2.exceptions.BaseError:
                raise UiError(*ERROR_MSG_0046)

    def a_app_stop_all(self):
        """停止所有app"""
        self.base_data.android.app_stop_all()

    def a_app_stop_appoint(self, package_name_list: list):
        """停止除指定app外所有app"""
        if package_name_list:
            try:
                self.base_data.android.app_stop_all(excludes=package_name_list)
            except uiautomator2.exceptions.BaseError:
                raise UiError(*ERROR_MSG_0046)
        else:
            raise UiError(*ERROR_MSG_0046)
