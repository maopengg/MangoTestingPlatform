from uiautomator2.xpath import XPath
from auto_ui.app_auto_base import ElementNotFoundError, ElementNotDisappearError
from auto_ui.app_auto_base.android_base import AndroidBase
from utlis.logs.log_control import ERROR, INFO


class ElementOperation(AndroidBase):
    """元素操作类"""

    def click(self, element):
        """单击"""
        try:
            self.find_element(element).click_exists(timeout=3)
            INFO.logger.info("成功单击")
        except Exception as e:
            ERROR.logger.error(f"无法单击，元素：{element}，报错信息：{e}")
            return None

    def double_click(self, system, element):
        """双击"""
        try:
            if system == "android":
                self.app.double_click(*self.find_element(element).center())
            else:
                self.app.double_tap(*self.find_element(element).center())
            INFO.logger.info("成功双击")
        except Exception as e:
            ERROR.logger.error(f"无法双击，元素：{element}，报错信息：{e}")
            return None

    def long_click(self, element, second):
        """长按"""
        try:
            self.find_element(element).long_click(second)
            INFO.logger.info("成功长按%sS" % str(second))
        except Exception as e:
            ERROR.logger.error(f"无法长按%，元素：{element}，时间：{second}，报错信息：{e}")
            return None

    def click_coord(self, x, y):
        """坐标单击 百分比或坐标值"""
        try:
            self.app.click(x, y)
            INFO.logger.info(f"成功坐标单击：x-{x}, y-{y}")
        except Exception as e:
            ERROR.logger.error(f"无法坐标单击：x-{x}, y-{y}，报错信息：{e}")
            return None

    def double_click_coord(self, x, y):
        """坐标双击 百分比或坐标值"""
        try:
            self.app.double_click(x, y)
            INFO.logger.info("成功坐标双击")
        except Exception as e:
            ERROR.logger.error(f"无法坐标双击，x-{x}, y-{y}，报错信息：{e}")
            return None

    def long_click_coord(self, x, y, second):
        """坐标长按 百分比或坐标值"""
        try:
            self.app.tap_hold(x, y, second)
            INFO.logger.info("成功坐标长按%sS" % str(second))
        except Exception as e:
            ERROR.logger.error(f"无法双击，x-{x}, y-{y}，长按时间：{second}，报错信息：{e}")
            return None

    def swipe(self, fx, fy, tx, ty, duration=None):
        """坐标滑动 百分比或坐标值"""
        try:
            if duration == "":
                duration = None
            self.app.swipe(fx, fy, tx, ty, duration)
            INFO.logger.info("成功执行滑动")
        except Exception as e:
            ERROR.logger.error(f"无法执行滑动，坐标：{fx, fy, tx, ty}，报错信息：{e}")
            return None

    def input_text(self, element, text):
        """输入"""
        try:
            self.find_element(element).set_text(text)
            INFO.logger.info("成功输入%s" % str(text))
        except Exception as e:
            ERROR.logger.error(f"无法输入，元素：{element}，输入：{text}，报错信息：{e}")
            return None

    def clear_text(self, element):
        """清空输入框"""
        try:
            ele = self.find_element(element)
            xe = ele.get()
            ele._d.set_fastinput_ime()
            xe.click()
            ele._parent._d.set_fastinput_ime()
            ele._parent._d.clear_text()
            INFO.logger.info("成功清空")
        except Exception as e:
            ERROR.logger.error(f"无法清空元素：{element}，报错信息：{e}")
            return None

    def scroll_to_ele(self, element, direction):
        """滑动到元素出现"""
        try:
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
            INFO.logger.info("成功滑动到元素出现")
        except Exception as e:
            ERROR.logger.error(f"无法滑动到元素出现，元素：{element}，滑动方向：{direction}，报错信息：{e}")
            return None

    def pinch_in(self, element):
        """缩小 安卓仅支持属性定位"""
        try:
            self.find_element(element).pinch_in()
            INFO.logger.info("成功缩小")
        except Exception as e:
            ERROR.logger.error(f"无法缩小，元素：{element}，报错信息：{e}")
            return None

    def pinch_out(self, element):
        """放大 安卓仅支持属性定位"""
        try:
            self.find_element(element).pinch_out()
            INFO.logger.info("成功放大")
        except Exception as e:
            ERROR.logger.error(f"无法放大，元素：{element}，报错信息：{e}")
            return None

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
            return None
        except Exception as e:
            ERROR.logger.error(f"无法等待元素出现，元素：{element}，报错信息：{e}")
            return None

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
            return None
        except Exception as e:
            ERROR.logger.error(f"无法等待元素消失，元素：{element}，报错信息：{e}")
            return None

    def drag_to_ele(self, start_element, end_element):
        """拖动到元素 只支持属性定位"""
        try:
            self.find_element(start_element).drag_to(**end_element)
            INFO.logger.info("成功拖动到元素")
        except Exception as e:
            ERROR.logger.error(f"无法拖动到元素，拖拽元素：{start_element}，到达元素：{end_element}，报错信息：{e}")
            return None

    def drag_to_coord(self, element, x, y):
        """拖动到坐标 只支持属性定位"""
        try:
            self.find_element(element).drag_to(x, y)
            INFO.logger.info("成功拖动到坐标")
        except Exception as e:
            ERROR.logger.error(f"无法拖动到坐标，拖拽元素：{element}，到达坐标{x, y}，报错信息：{e}")
            return None

    def drag_coord(self, fx, fy, tx, ty):
        """坐标拖动"""
        try:
            self.app.drag(fx, fy, tx, ty)
            INFO.logger.info("成功坐标拖动")
        except Exception as e:
            ERROR.logger.error(f"无法坐标拖动，拖拽坐标：{fx, fy}，到达坐标{tx, ty}，报错信息：{e}")
            return None

    def swipe_ele(self, element, direction):
        """元素内滑动"""
        try:
            self.find_element(element).swipe(direction)
            INFO.logger.info("成功元素内滑动")
        except Exception as e:
            ERROR.logger.error(f"无法元素内滑动，滑动元素：{element}，到达位置：{direction}，报错信息：{e}")
            return None
