# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
from autotest.ui.base_tools.android.application import UiautomatorApplication
from autotest.ui.base_tools.android.customization import UiautomatorCustomization
from autotest.ui.base_tools.android.element import UiautomatorElement
from autotest.ui.base_tools.android.equipment import UiautomatorEquipment
from autotest.ui.base_tools.android.page import UiautomatorPage


class AndroidDriver(UiautomatorEquipment,
                    UiautomatorApplication,
                    UiautomatorPage,
                    UiautomatorElement,
                    UiautomatorCustomization):
    pass
