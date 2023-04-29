# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-11 17:25
# @Author : 毛鹏

from uiautomator2 import Device

from enum_class.ui_enum import EleExp
from utlis.logs.log_control import ERROR, INFO

"""
python -m uiautomator2 init
python -m weditor

"""


class AndroidBase:
    """app基类"""

    def __init__(self, equipment):
        self.app = Device(equipment)
        try:
            INFO.logger.info(f'设备信息：{self.app.info}')
        except RuntimeError as e:
            ERROR.logger.error(f'设备启动异常，请检查设备连接！报错内容：{e}')
        self.app.implicitly_wait(10)

    def __new__(cls, *args, **kwargs):
        if not hasattr(AndroidBase, 'instance'):
            cls.instance = super().__new__(cls)
        return cls.instance

    def ele(self, locator: str, _type: int):
        return {
            EleExp.XPATH.value: self.app.xpath(locator),
            EleExp.ID.value: self.app(resourceId=locator),
            EleExp.BOUNDS.value: self.app(text=locator),
            EleExp.DESCRIPTION.value: self.app(description=locator)
        }.get(_type)

    def find_element(self, locator: str):
        """
        判断元素是否存在并定位该元素
        :param locator: 元素定位方式，可以是xpath或者百分比坐标
        :return: 元素对象
        """
        try:
            return self.app.xpath(locator)
        except Exception as e:
            ERROR.logger.error(f"元素表达式有误，元素：{locator}，报错信息：{e}")
