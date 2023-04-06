# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏

from auto_ui.app_auto_base.assertionOpt import Assertion
from auto_ui.app_auto_base.element import ElementOperation
from auto_ui.app_auto_base.device import EquipmentDevice
from auto_ui.app_auto_base.page import Page


class AppRun(Page, EquipmentDevice, ElementOperation, Assertion):

    def __init__(self, equipment: str = '8796a033'):
        super().__init__(equipment)

    def case_along(self, case_data: list):
        for i in case_data:
            self.action_element(i)
        return True

    def action_element(self, element: dict):
        # 查询元素是否存在
        pass


if __name__ == '__main__':
    r = AppRun()
    # r.start_app('com.tencent.mm')
