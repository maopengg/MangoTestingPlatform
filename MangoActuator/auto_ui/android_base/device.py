from time import sleep
from utlis.logs.log_control import ERROR, INFO

from .android_base import AndroidBase


class EquipmentDevice(AndroidBase):
    """设备操作"""

    def start_app(self, app_name):
        """启动应用"""
        try:
            self.app.app_start(app_name)
            INFO.logger.info("成功执行启动应用")
        except Exception as e:
            ERROR.logger.error(f"无法执行打开应用，包名：{app_name}，报错信息：{e}")
            return None

    def close_app(self, app_name):
        """关闭应用"""
        try:
            self.app.app_stop(app_name)
            INFO.logger.info("成功执行关闭应用")
            sleep(1)
        except Exception as e:
            ERROR.logger.error(f"无法执行关闭应用，包名：{app_name}，报错信息：{e}")
            return None

    def swipe_left(self):
        """左滑"""
        try:
            self.app.swipe_ext("left")
            INFO.logger.info("成功执行左滑")
        except Exception as e:
            ERROR.logger.error(f"无法执行左滑，报错信息：{e}")
            return None

    def swipe_right(self):
        """右滑"""
        try:
            self.app.swipe_ext("right")
            INFO.logger.info("成功执行右滑")
        except Exception as e:
            ERROR.logger.error(f"无法执行右滑，报错信息：{e}")
            return None

    def swipe_up(self):
        """上滑"""
        try:
            self.app.swipe_ext("up")
            INFO.logger.info("成功执行上滑")
        except Exception as e:
            ERROR.logger.error(f"无法执行上滑，报错信息：{e}")
            return None

    def swipe_down(self):
        """下滑"""
        try:
            self.app.swipe_ext("down")
            INFO.logger.info("成功执行下滑")
        except Exception as e:
            ERROR.logger.error(f"无法执行下滑，报错信息：{e}")
            return None

    def home(self):
        """返回首页"""
        try:
            self.app.keyevent("home")
            INFO.logger.info("成功执行返回系统首页")
        except Exception as e:
            ERROR.logger.error(f"无法执行返回系统首页，报错信息：{e}")
            return None

    def back(self):
        """返回一步"""
        try:
            self.app.keyevent("back")
            INFO.logger.info("成功执行返回")
        except Exception as e:
            ERROR.logger.error(f"无法执行返回，报错信息：{e}")
            return None

    def press(self, keycode):
        """操作设备按钮"""
        try:
            self.app.press(keycode)
            INFO.logger.info("成功执行按下系统键位: %s" % keycode)
        except Exception as e:
            ERROR.logger.error(f"无法执行按下系统键位: {keycode}，报错信息：{e}")
            return None

    def screenshot(self, filepath):
        """屏幕截图"""
        try:
            self.app.screenshot(filename=filepath)
            INFO.logger.info("成功执行屏幕截图")
        except Exception as e:
            ERROR.logger.error(f"无法执行屏幕截图，保存文件路径{filepath}，报错信息：{e}")
            return None

    def screen_on(self):
        """亮屏"""
        try:
            self.app.screen_on()
            INFO.logger.info("成功执行亮屏")
        except Exception as e:
            ERROR.logger.error(f"无法执行亮屏，报错信息：{e}")
            return None

    def screen_off(self):
        """息屏"""
        try:
            self.app.screen_off()
            INFO.logger.info("成功执行息屏")
        except Exception as e:
            ERROR.logger.error(f"无法执行息屏，报错信息：{e}")
            return None

    def sleep(self, second):
        """强制等待"""
        try:
            sleep(second)
            INFO.logger.info("成功执行sleep %ds" % second)
        except Exception as e:
            ERROR.logger.error(f"无法执行sleep，时间：{second}，报错信息：{e}")
            return None

    def implicitly_wait(self, second):
        """隐式等待"""
        try:
            self.app.implicitly_wait(second)
            INFO.logger.info("成功执行implicitly wait %ds" % second)
        except Exception as e:
            ERROR.logger.error(f"无法执行implicitly wait 时间：{second}，报错信息：{e}")
            return None

    def get_window_size(self):
        """提取屏幕尺寸"""
        try:
            w, h = self.app.window_size()
            INFO.logger.info("成功获取屏幕尺寸:%s" % str(w, h))
            return w, h
        except Exception as e:
            ERROR.logger.error(f"无法获取屏幕尺寸，{e}")
            return None
