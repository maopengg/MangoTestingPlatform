from uiautomator2 import UiObject

from auto_ui.android_base.android_base import AndroidBase
from utils.assertion.public_assertion import PublicAssertion
from utils.logs.log_control import ERROR, INFO


class UiautomatorAssertion(AndroidBase):
    """安卓断言"""

    def a_assert_ele_exists(self, locating: UiObject, assertion, expect):
        """断言元素存在"""
        try:
            actual = locating.exists
            INFO.logger.info("成功获取元素exists:%s" % str(actual))
        except Exception as e:
            ERROR.logger.error("无法获取元素exists")
            raise e
        else:
            result, msg = PublicAssertion(assertion, actual, expect).compare()
            return result, msg

    def a_assert_ele_text(self, locating: UiObject, assertion, expect):
        """断言元素文本"""
        try:
            actual = locating.get_text()
            INFO.logger.info("成功获取元素text:%s" % str(actual))
        except Exception as e:
            ERROR.logger.error("无法获取元素text")
            raise e
        else:
            result, msg = PublicAssertion(assertion, actual, expect).compare()
            return result, msg

    def a_assert_ele_attribute(self, locating: UiObject, attribute, assertion, expect):
        """断言元素属性"""
        try:
            actual = locating.info[attribute]
            INFO.logger.info("成功获取元素%s属性:%s" % (attribute, str(actual)))
        except Exception as e:
            ERROR.logger.error("无法获取元素%s属性" % attribute)
            raise e
        else:
            result, msg = PublicAssertion(assertion, actual, expect).compare()
            return result, msg

    def a_assert_ele_center(self, locating: UiObject, assertion, expect):
        """断言元素位置"""
        try:
            x, y = locating.center()
            actual = (x, y)
            INFO.logger.info("成功获取元素位置:%s" % str(actual))
        except Exception as e:
            ERROR.logger.error("无法获取元素位置")
            raise e
        else:
            result, msg = PublicAssertion(assertion, str(actual), expect).compare()
            return result, msg

    def a_assert_ele_x(self, locating: UiObject, assertion, expect):
        """断言元素X坐标"""
        try:
            x, y = locating.center()
            actual = x
            INFO.logger.info("成功获取元素X坐标:%s" % str(actual))
        except Exception as e:
            ERROR.logger.error("无法获取元素X坐标")
            raise e
        else:
            result, msg = PublicAssertion(assertion, actual, expect).compare()
            return result, msg

    def a_assert_ele_y(self, locating: UiObject, assertion, expect):
        """断言元素Y坐标"""
        try:
            x, y = locating.center()
            actual = y
            INFO.logger.info("成功获取元素Y坐标:%s" % str(actual))
        except Exception as e:
            ERROR.logger.error("无法获取元素Y坐标")
            raise e
        else:
            result, msg = PublicAssertion(assertion, actual, expect).compare()
            return result, msg
