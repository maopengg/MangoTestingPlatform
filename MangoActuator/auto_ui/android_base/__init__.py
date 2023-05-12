from auto_ui.android_base.application import UiautomatorApplication
from auto_ui.android_base.assertion import UiautomatorAssertion
from auto_ui.android_base.element import UiautomatorElementOperation
from auto_ui.android_base.equipment import UiautomatorEquipmentDevice
from auto_ui.android_base.page import UiautomatorPage


class DriverMerge(UiautomatorAssertion,
                  UiautomatorEquipmentDevice,
                  UiautomatorElementOperation,
                  UiautomatorPage,
                  UiautomatorApplication):
    pass
