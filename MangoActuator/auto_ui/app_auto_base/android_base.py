# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-11 17:25
# @Author : 毛鹏

import uiautomator2

from utlis.logs.log_control import ERROR

"""
python -m uiautomator2 init
python -m weditor

"""


class AndroidBase:
    """app基类"""

    def __init__(self, equipment):
        self.app = uiautomator2.connect(equipment)
        self.app.implicitly_wait(10)

    def find_element(self, locator: str):
        """
        判断元素是否存在并定位该元素
        :param locator: 元素定位方式，可以是xpath或者百分比坐标
        :return: 元素对象
        """
        try:
            return self.app.xpath(locator)
        except Exception:
            ERROR.logger.error("元素表达式有误: {}".format(locator))
