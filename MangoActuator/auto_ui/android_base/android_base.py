# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-11 17:25
# @Author : 毛鹏

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
    app.implicitly_wait(10)
    return app


if __name__ == '__main__':
    r = new_android()
    r.app_start('com.tencent.mm')
    print(type(r))
