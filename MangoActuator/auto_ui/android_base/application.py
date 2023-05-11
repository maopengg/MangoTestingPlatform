from auto_ui.android_base.android_base import AndroidBase
from utils.logs.log_control import ERROR, INFO


class UiautomatorApplication(AndroidBase):
    """应用操作"""

    def start_app(self, app_name):
        """启动应用"""
        try:
            self.android.app_start(app_name)
            self.sleep(5)
            INFO.logger.info("成功执行启动应用")
        except Exception as e:
            ERROR.logger.error(f"无法执行打开应用，包名：{app_name}，报错信息：{e}")
            return None

    def close_app(self, app_name):
        """关闭应用"""
        try:
            self.android.app_stop(app_name)
            INFO.logger.info("成功执行关闭应用")
            self.sleep(1)
        except Exception as e:
            ERROR.logger.error(f"无法执行关闭应用，包名：{app_name}，报错信息：{e}")
            return None

    def clear_app(self, app_name):
        """清除app数据"""
        try:
            self.android.app_clear(app_name)
            INFO.logger.info("成功执行关闭应用")
            self.sleep(1)
        except Exception as e:
            ERROR.logger.error(f"无法执行清除app数据，包名：{app_name}，报错信息：{e}")
            return None

    def app_stop_all(self):
        """停止所有app"""
        self.android.app_stop_all()

    def app_stop_appoint(self, app_list: list):
        """停止除指定app外所有app"""
        self.android.app_stop_all(excludes=app_list)
