from uiautomator2 import Device, UiObject
from uiautomator2.xpath import XPath

from utils.logs.log_control import ERROR, INFO


class UiautomatorElementOperation:
    """元素操作类"""

    def __init__(self, android: Device = None):
        self.android = android

    def click(self, element: UiObject):
        """单击"""
        element.click()

    def double_click(self, element: UiObject):
        """双击"""
        self.android.double_click(element.center())

    def long_click(self, element: UiObject, second):
        """长按"""
        element.long_click(second)

    def click_coord(self, x, y):
        """坐标单击 百分比或坐标值"""
        self.app.click(x, y)

    def double_click_coord(self, x, y):
        """坐标双击 百分比或坐标值"""
        self.app.double_click(x, y)

    def long_click_coord(self, x, y, second):
        """坐标长按 百分比或坐标值"""
        self.app.tap_hold(x, y, second)

    def swipe(self, fx, fy, tx, ty, duration=None):
        """坐标滑动 百分比或坐标值"""
        if duration == "":
            duration = None
        self.app.swipe(fx, fy, tx, ty, duration)

    def input_text(self, element, text):
        """输入"""
        self.find_element(element).set_text(text)

    def clear_text(self, element):
        """清空输入框"""
        self.find_element(element).clear_text()

    def scroll_to_ele(self, element, direction):
        """滑动到元素出现"""
        if "xpath" in element:
            XPath(self.app).scroll_to(element["xpath"], direction)
        elif direction == "up":
            self.app(scrollable=True).forward.to(**element)
        elif direction == "down":
            self.app(scrollable=True).backward.to(**element)
        elif direction == "left":
            self.app(scrollable=True).horiz.forward.to(**element)
        else:
            self.app(scrollable=True).horiz.backward.to(**element)

    def pinch_in(self, element):
        """缩小 安卓仅支持属性定位"""
        self.find_element(element).pinch_in()

    def pinch_out(self, element):
        """放大 安卓仅支持属性定位"""
        self.find_element(element).pinch_out()

    def wait(self, element, second):
        """等待元素出现"""
        try:
            if self.find_element(element).wait(timeout=second):
                INFO.logger.info("成功等待元素出现")
            else:
                ERROR.logger.error("等待元素出现失败 元素不存在")
                raise ElementNotFoundError("element not exists")
        except ElementNotFoundError as e:
            ERROR.logger.error(f"元素可能不存在，元素：{element}，报错信息：{e}")
            return False
        except Exception as e:
            ERROR.logger.error(f"无法等待元素出现，元素：{element}，报错信息：{e}")
            return False

    def wait_gone(self, element, second):
        """等待元素消失"""
        try:
            res = self.find_element(element).wait_gone(timeout=second)
            if res:
                INFO.logger.info("成功等待元素消失")
            else:
                ERROR.logger.error("等待元素消失失败 元素仍存在")
                raise ElementNotDisappearError("element exists")
        except ElementNotDisappearError as e:
            ERROR.logger.error(f"元素可能无法消失，元素：{element}，报错信息：{e}")
            return False
        except Exception as e:
            ERROR.logger.error(f"无法等待元素消失，元素：{element}，报错信息：{e}")
            return False

    def drag_to_ele(self, start_element, end_element):
        """拖动到元素 只支持属性定位"""
        try:
            self.find_element(start_element).drag_to(**end_element)
            INFO.logger.info("成功拖动到元素")
        except Exception as e:
            ERROR.logger.error(f"无法拖动到元素，拖拽元素：{start_element}，到达元素：{end_element}，报错信息：{e}")
            return False

    def drag_to_coord(self, element, x, y):
        """拖动到坐标 只支持属性定位"""
        self.find_element(element).drag_to(x, y)

    def drag_coord(self, fx, fy, tx, ty):
        """坐标拖动"""
        self.app.drag(fx, fy, tx, ty)

    def swipe_ele(self, element, direction):
        """元素内滑动"""
        self.find_element(element).swipe(direction)
