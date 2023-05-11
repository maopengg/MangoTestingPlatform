# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-11 17:25
# @Author : 毛鹏
from time import sleep
from uiautomator2 import Device

from utils.logs.log_control import ERROR, INFO

"""
python -m uiautomator2 init
python -m weditor

"""


def new_android(equipment='8796a033') -> Device:
    app = Device(equipment)
    try:
        INFO.logger.info(f'设备信息：{app.info}')
    except RuntimeError as e:
        ERROR.logger.error(f'设备启动异常，请检查设备连接！报错内容：{e}')
    return app


class AndroidBase:

    # def __init__(self, android: Device = None):
    #     self.android = android
    #     self.android.implicitly_wait(10)

    def sleep(self, second):
        """强制等待"""
        try:
            sleep(second)
        except Exception as e:
            ERROR.logger.error(f"无法执行sleep，时间：{second}，报错信息：{e}")
            return None


class ElementNotFoundError(Exception):
    """元素获取失败"""


class ElementNotDisappearError(Exception):
    """元素消失失败"""


if __name__ == '__main__':
    r = new_android()
    r.app_start('com.tencent.mm')
    print(type(r))
