from threading import Thread
import os
from django.apps import AppConfig

from src.tools import is_main_process


class AutoUiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_ui'

    def ready(self):
        # 多进程保护机制，防止在多进程环境下重复执行
        if is_main_process():
            return

        def run():
            try:
                pass
            except (RuntimeError, SystemError) as e:
                # 忽略进程关闭时的错误（开发服务器重载时常见）
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ['shutdown', 'interpreter', 'cannot schedule', 'after shutdown']):
                    return
                raise

        # 设置为 daemon 线程，确保在服务关闭时能够快速退出
        task = Thread(target=run, daemon=True)
        task.start()
