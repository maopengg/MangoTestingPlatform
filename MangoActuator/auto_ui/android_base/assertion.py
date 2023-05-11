from uiautomator2 import UiObject

from auto_ui.android_base.android_base import AndroidBase
from utils.assertion.assertion import LMAssert
from utils.logs.log_control import ERROR, INFO


class UiautomatorAssertion(AndroidBase):
    """断言类操作"""

    def assert_ele_exists(self, element: UiObject, assertion, expect):
        """断言元素存在"""
        try:
            actual = element.exists
            INFO.logger.info("成功获取元素exists:%s" % str(actual))
        except Exception as e:
            ERROR.logger.error("无法获取元素exists")
            raise e
        else:
            result, msg = LMAssert(assertion, actual, expect).compare()
            return result, msg

    def assert_ele_text(self, element: UiObject, assertion, expect):
        """断言元素文本"""
        try:
            actual = element.get_text()
            INFO.logger.info("成功获取元素text:%s" % str(actual))
        except Exception as e:
            ERROR.logger.error("无法获取元素text")
            raise e
        else:
            result, msg = LMAssert(assertion, actual, expect).compare()
            return result, msg

    def assert_ele_attribute(self, element: UiObject, attribute, assertion, expect):
        """断言元素属性"""
        try:
            actual = element.info[attribute]
            INFO.logger.info("成功获取元素%s属性:%s" % (attribute, str(actual)))
        except Exception as e:
            ERROR.logger.error("无法获取元素%s属性" % attribute)
            raise e
        else:
            result, msg = LMAssert(assertion, actual, expect).compare()
            return result, msg

    def assert_ele_center(self, element: UiObject, assertion, expect):
        """断言元素位置"""
        try:
            x, y = element.center()
            actual = (x, y)
            INFO.logger.info("成功获取元素位置:%s" % str(actual))
        except Exception as e:
            ERROR.logger.error("无法获取元素位置")
            raise e
        else:
            result, msg = LMAssert(assertion, str(actual), expect).compare()
            return result, msg

    def assert_ele_x(self, element: UiObject, assertion, expect):
        """断言元素X坐标"""
        try:
            x, y = element.center()
            actual = x
            INFO.logger.info("成功获取元素X坐标:%s" % str(actual))
        except Exception as e:
            ERROR.logger.error("无法获取元素X坐标")
            raise e
        else:
            result, msg = LMAssert(assertion, actual, expect).compare()
            return result, msg

    def assert_ele_y(self, element: UiObject, assertion, expect):
        """断言元素Y坐标"""
        try:
            x, y = element.center()
            actual = y
            INFO.logger.info("成功获取元素Y坐标:%s" % str(actual))
        except Exception as e:
            ERROR.logger.error("无法获取元素Y坐标")
            raise e
        else:
            result, msg = LMAssert(assertion, actual, expect).compare()
            return result, msg
