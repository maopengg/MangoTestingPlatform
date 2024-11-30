from uiautomation.uiautomation import ButtonControl

from src.services.ui.bases.base_data import BaseData


class WinElement(BaseData):
    """元素操作"""

    def win_click(self, locating: ButtonControl):
        self.windows.ButtonControl(Name='五').Click(simulateMove=False)

    def win_input(self, locating: ButtonControl):
        locating.ButtonControl(Name='五')
