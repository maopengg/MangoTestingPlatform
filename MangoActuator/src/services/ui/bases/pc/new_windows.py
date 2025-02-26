# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-30 13:12
# @Author : 毛鹏
import platform
import subprocess
from typing import Optional

if platform.system() != "Linux":
    import uiautomation as auto
    from uiautomation.uiautomation import WindowControl

    from src.models.ui_model import EquipmentModel


    class NewWindows:

        def __init__(self, web_config: EquipmentModel = None):
            self.config = web_config
            self.windows: Optional[None | WindowControl] = None

        def new_windows(self):
            subprocess.Popen(self.config.win_path)
            self.windows = auto.WindowControl(ClassName='ApplicationFrameWindow', Name=self.config.win_title)
            return self.windows

else:
    class NewWindows:
        pass
