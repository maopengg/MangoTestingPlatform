import sys
from time import sleep

from uiautomator2 import UiObjectNotFoundError
from wda import WDAElementNotFoundError

from utlis.logs.log_control import ERROR, INFO
from .android_base import AndroidBase


class System(AndroidBase):
    """系统操作"""

    def start_app(self, app_id):
        """启动应用"""
        try:
            self.app.app_start(app_id)
            INFO.logger.info("成功执行启动应用")
        except Exception as e:
            ERROR.logger.error("无法执行关闭应用")
            raise e

    def close_app(self, app_id):
        """关闭应用"""
        try:
            self.app.app_stop(app_id)
            INFO.logger.info("成功执行关闭应用")
        except Exception as e:
            ERROR.logger.error("无法执行关闭应用")
            raise e

    def swipe_left(self, system):
        """左滑"""
        try:
            if system == "android":
                self.app.swipe_ext("left")
            else:
                self.app.swipe_left()
            INFO.logger.info("成功执行左滑")
        except Exception as e:
            ERROR.logger.error("无法执行左滑")
            raise e

    def swipe_right(self, system):
        """右滑"""
        try:
            if system == "android":
                self.app.swipe_ext("right")
            else:
                self.app.swipe_right()
            INFO.logger.info("成功执行右滑")
        except Exception as e:
            ERROR.logger.error("无法执行右滑")
            raise e

    def swipe_up(self, system):
        """上滑"""
        try:
            if system == "android":
                self.app.swipe_ext("up")
            else:
                self.app.swipe_up()
            INFO.logger.info("成功执行上滑")
        except Exception as e:
            ERROR.logger.error("无法执行上滑")
            raise e

    def swipe_down(self, system):
        """下滑"""
        try:
            if system == "android":
                self.app.swipe_ext("down")
            else:
                self.app.swipe_down()
            INFO.logger.info("成功执行下滑")
        except Exception as e:
            ERROR.logger.error("无法执行下滑")
            raise e

    def home(self, system):
        """系统首页"""
        try:
            if system == "android":
                self.app.keyevent("home")
            else:
                self.app.home()
            INFO.logger.info("成功执行返回系统首页")
        except Exception as e:
            ERROR.logger.error("无法执行返回系统首页")
            raise e

    def back(self):
        """系统返回 安卓专用"""
        try:
            self.app.keyevent("back")
            INFO.logger.info("成功执行返回")
        except Exception as e:
            ERROR.logger.error("无法执行返回")
            raise e

    def press(self, keycode):
        """系统按键"""
        try:
            self.app.press(keycode)
            INFO.logger.info("成功执行按下系统键位: %s" % keycode)
        except Exception as e:
            ERROR.logger.error("无法执行按下系统键位: %s" % keycode)
            raise e

    def screenshot(self, name):
        """屏幕截图"""
        try:
            screenshot = self.app.screenshot(format='raw')
            self.test.saveScreenShot(name, screenshot)
            INFO.logger.info("成功执行屏幕截图")
        except Exception as e:
            ERROR.logger.error("无法执行屏幕截图")
            raise e

    def screen_on(self, system):
        """亮屏"""
        try:
            if system == "android":
                self.app.screen_on()
            else:
                self.app.unlock()
            INFO.logger.info("成功执行亮屏")
        except Exception as e:
            ERROR.logger.error("无法执行亮屏")
            raise e

    def screen_off(self, system):
        """息屏"""
        try:
            if system == "android":
                self.app.screen_off()
            else:
                self.app.lock()
            INFO.logger.info("成功执行息屏")
        except Exception as e:
            ERROR.logger.error("无法执行息屏")
            raise e

    def sleep(self, second):
        """强制等待"""
        try:
            sleep(second)
            INFO.logger.info("成功执行sleep %ds" % second)
        except Exception as e:
            ERROR.logger.error("无法执行sleep %ds" % second)
            raise e

    def implicitly_wait(self, second):
        """隐式等待"""
        try:
            self.app.implicitly_wait(second)
            INFO.logger.info("成功执行implicitly wait %ds" % second)
        except Exception as e:
            ERROR.logger.error("无法执行implicitly wait %ds" % second)
            raise e

    def custom(self, **kwargs):
        """自定义"""
        code = kwargs["code"]
        names = locals()
        names["element"] = kwargs["element"]
        names["data"] = kwargs["data"]
        names["device"] = self.app
        names["test"] = self.test
        try:
            def print(*args, sep=' ', end='\n', file=None, flush=False):
                if file is None or file in (sys.stdout, sys.stderr):
                    file = names["test"].stdout_buffer
                self.print(*args, sep=sep, end=end, file=file, flush=flush)

            def sys_get(name):
                if name in names["test"].context:
                    return names["test"].context[name]
                elif name in names["test"].common_params:
                    return names["test"].common_params[name]
                else:
                    raise KeyError("不存在的公共参数或关联变量: {}".format(name))

            def sys_put(name, val, ps=False):
                if ps:
                    names["test"].common_params[name] = val
                else:
                    names["test"].context[name] = val

            exec(code)
            INFO.logger.info("成功执行 %s" % kwargs["trans"])
        except UiObjectNotFoundError as e:
            raise e
        except WDAElementNotFoundError as e:
            raise e
        except Exception as e:
            ERROR.logger.error("无法执行 %s" % kwargs["trans"])
            raise e
