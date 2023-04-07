# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-11 17:25
# @Author : 毛鹏

import uiautomator2

from auto_ui.tools.enum import AppExp
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

    def ele(self, ele: str, _type: int):
        # if _type == AppExp.XPATH.value:
        #     return self.app.xpath(ele)
        # elif _type == AppExp.ID.value:
        #     return self.app(resourceId=ele)
        # elif _type == AppExp.BOUNDS.value:
        #     return self.app(text=ele)
        # elif _type == AppExp.DESCRIPTION.value:
        #     return self.app(description=ele)
        return {
            AppExp.XPATH.value: self.app.xpath(ele),
            AppExp.ID.value: self.app(resourceId=ele),
            AppExp.BOUNDS.value: self.app(text=ele),
            AppExp.DESCRIPTION.value: self.app(description=ele)
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
