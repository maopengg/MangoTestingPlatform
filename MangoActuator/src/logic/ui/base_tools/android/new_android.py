# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-05-23 15:05
# @Author : 毛鹏

import uiautomator2 as us
from adbutils import AdbTimeout

from src.exceptions import NewObjectError
from src.models.socket_model.ui_model import AndroidConfigModel
from src.tools.desktop.signal_send import SignalSend
from src.tools import ERROR_MSG_0042, ERROR_MSG_0045, ERROR_MSG_0047

"""
python -m uiautomator2 init
python -m weditor

"""


class NewAndroid:

    def __init__(self, android_config: AndroidConfigModel = None):
        self.android_config = android_config

    def new_android(self):
        SignalSend.notice_signal_c('正在创建安卓设备')
        if self.android_config is None:
            raise NewObjectError(*ERROR_MSG_0042)
        android = us.connect(self.android_config.equipment)

        try:
            SignalSend.notice_signal_c(f"设备启动成功！产品名称：{android.info.get('productName')}")
        except RuntimeError:
            SignalSend.notice_signal_c(ERROR_MSG_0045[1].format(self.android_config.equipment))
            raise NewObjectError(*ERROR_MSG_0045, value=(self.android_config.equipment,))
        except (AdbTimeout, TimeoutError):
            SignalSend.notice_signal_c(ERROR_MSG_0047[1].format(self.android_config.equipment))
            raise NewObjectError(*ERROR_MSG_0047, value=(self.android_config.equipment,))
        else:
            android.implicitly_wait(10)
            return android
