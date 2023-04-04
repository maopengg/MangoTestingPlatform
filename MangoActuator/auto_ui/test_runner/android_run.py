# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏
from auto_ui.android_auto_base.android_base import AndroidBase


class AndroidRun(AndroidBase):

    def __init__(self, equipment, package):
        super().__init__(equipment, package)

    def app(self):
        self.launch_app()

    def case_along(self, case_data: list):
        for i in case_data:
            self.action_element(i)
        return True

    def action_element(self, element: dict):
        # 查询元素是否存在
        pass
