from uiautomator2 import Device

from utils.assertion.assertion import LMAssert
from utils.logs.log_control import ERROR, INFO


class UiautomatorAssertion:
    """断言类操作"""

    def __init__(self, android: Device = None):
        self.android = android

    def assert_ele_exists(self, element, assertion, expect):
        """断言元素存在"""
        try:
            actual = find_element(element).exists
            INFO.logger.info("成功获取元素exists:%s" % str(actual))
        except Exception as e:
            ERROR.logger.error("无法获取元素exists")
            raise e
        else:
            result, msg = LMAssert(assertion, actual, expect).compare()
            return result, msg

    def assert_ele_text(self, system, element, assertion, expect):
        """断言元素文本"""
        try:
            if system == "android":
                actual = self.find_element(element).get_text()
            else:
                actual = self.find_element(element).text()
            INFO.logger.info("成功获取元素text:%s" % str(actual))
        except Exception as e:
            ERROR.logger.error("无法获取元素text")
            raise e
        else:
            result, msg = LMAssert(assertion, actual, expect).compare()
            return result, msg

    def assert_ele_attribute(self, element, attribute, assertion, expect):
        """断言元素属性"""
        try:
            actual = self.find_element(element).info[attribute]
            INFO.logger.info("成功获取元素%s属性:%s" % (attribute, str(actual)))
        except Exception as e:
            ERROR.logger.error("无法获取元素%s属性" % attribute)
            raise e
        else:
            result, msg = LMAssert(assertion, actual, expect).compare()
            return result, msg

    def assert_ele_center(self, system, element, assertion, expect):
        """断言元素位置"""
        try:
            if system == "android":
                x, y = self.find_element(element).center()
                actual = (x, y)
            else:
                x, y = self.find_element(element).bounds.center
                actual = (x, y)
            INFO.logger.info("成功获取元素位置:%s" % str(actual))
        except Exception as e:
            ERROR.logger.error("无法获取元素位置")
            raise e
        else:
            result, msg = LMAssert(assertion, str(actual), expect).compare()
            return result, msg

    def assert_ele_x(self, system, element, assertion, expect):
        """断言元素X坐标"""
        try:
            if system == "android":
                x, y = self.find_element(element).center()
                actual = x
            else:
                x, y = self.find_element(element).bounds.center
                actual = x
            INFO.logger.info("成功获取元素X坐标:%s" % str(actual))
        except Exception as e:
            ERROR.logger.error("无法获取元素X坐标")
            raise e
        else:
            result, msg = LMAssert(assertion, actual, expect).compare()
            return result, msg

    def assert_ele_y(self, system, element, assertion, expect):
        """断言元素Y坐标"""
        try:
            if system == "android":
                x, y = self.find_element(element).center()
                actual = y
            else:
                x, y = self.find_element(element).bounds.center
                actual = y
            INFO.logger.info("成功获取元素Y坐标:%s" % str(actual))
        except Exception as e:
            ERROR.logger.error("无法获取元素Y坐标")
            raise e
        else:
            result, msg = LMAssert(assertion, actual, expect).compare()
            return result, msg
