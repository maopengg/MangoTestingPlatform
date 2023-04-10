# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-07 21:53
# @Author : 毛鹏
from auto_ui.android_base.assertion import Assertion
from auto_ui.android_base.device import EquipmentDevice
from auto_ui.android_base.element import ElementOperation
from auto_ui.android_base.page import Page


class DriverMerge(Page,
                  EquipmentDevice,
                  ElementOperation,
                  Assertion):
    pass
