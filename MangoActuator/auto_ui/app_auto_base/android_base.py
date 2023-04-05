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

    def __init__(self, equipment, package):
        self.app = uiautomator2.connect(equipment)
        self.package = package
        self.app.implicitly_wait(10)

    def find_element(self, locator: str or tuple):
        """
        判断元素是否存在并定位该元素
        :param locator: 元素定位方式，可以是xpath或者百分比坐标
        :return: 元素对象
        """
        try:
            # 如果locator是xpath，则使用xpath定位
            if locator.startswith("//"):
                element = self.app.xpath(locator)
            # 如果locator是百分比坐标，则使用click方法模拟点击操作
            elif "%" in locator:
                x, y = locator.split(",")
                x = float(x.strip("%")) / 100
                y = float(y.strip("%")) / 100
                self.app.click(x, y)
                element = True
            else:
                element = None
                ERROR.logger.error("元素表达式有误: {}".format(locator))
        except Exception as e:
            element = None
        return element
