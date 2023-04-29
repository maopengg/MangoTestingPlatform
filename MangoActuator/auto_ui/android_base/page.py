# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/4/6 13:31
# @Author : 毛鹏
from auto_ui.android_base.android_base import AndroidBase
from utlis.logs.log_control import ERROR, INFO


class Page(AndroidBase):
    """页面操作"""

    def get_ele_text(self, element):
        """提取元素文本"""
        try:
            actual = self.find_element(element).get_text()
            INFO.logger.info("成功获取元素文本:%s" % str(actual))
            return actual
        except Exception as e:
            ERROR.logger.error(f"无法获取元素文本，元素：{element}，报错信息：{e}")
            return None

    def get_ele_center(self, element):
        """提取元素位置"""
        try:
            x, y = self.find_element(element).center()
            INFO.logger.info("成功获取元素位置:%s" % str(x, y))
            return x, y
        except Exception as e:
            ERROR.logger.error(f"无法获取元素位置，元素：{element}，报错信息：{e}")
            return None

    def get_ele_x(self, element):
        """提取元素X Y坐标"""
        try:
            x, y = self.find_element(element).center()
            INFO.logger.info("成功获取元素X坐标:%s" % str(x, y))
            return x, y
        except Exception as e:
            ERROR.logger.error(f"无法获取元素X坐标，元素：{element}，报错信息：{e}")
            return None
