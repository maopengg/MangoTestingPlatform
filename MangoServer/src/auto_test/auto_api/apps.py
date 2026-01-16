from threading import Thread

import atexit
import time
from django.apps import AppConfig

from src.tools import is_main_process
from src.tools.log_collector import log


class AutoApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_api'

    def ready(self):
        # 多进程保护机制，防止在多进程环境下重复执行
        if is_main_process():
            return

        def run():
            try:
                time.sleep(10)
                self.test_case_consumption()
            except (RuntimeError, SystemError) as e:
                # 忽略进程关闭时的错误（开发服务器重载时常见）
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in
                       ['shutdown', 'interpreter', 'cannot schedule', 'after shutdown']):
                    return
                raise
            except Exception as e:
                # 其他异常记录日志但不影响启动
                import traceback
                log.api.error(f'API模块初始化异常: {e}')
                traceback.print_exc()

        task = Thread(target=run, daemon=True, name='AutoApiConfig-Init')
        task.start()
        # 只在主进程中注册退出处理函数，避免在开发服务器重载时被意外触发
        # 使用模块级别的标志确保只注册一次
        if not hasattr(AutoApiConfig, '_shutdown_registered'):
            atexit.register(self.shutdown)
            AutoApiConfig._shutdown_registered = True

    def test_case_consumption(self):
        from src.auto_test.auto_api.service.test_case.case_flow import ApiCaseFlow
        ApiCaseFlow.start()

    def shutdown(self):
        from src.auto_test.auto_api.service.test_case.case_flow import ApiCaseFlow
        ApiCaseFlow.stop()
