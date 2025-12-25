from threading import Thread
import os
from django.apps import AppConfig


class AutoUiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_ui'

    def ready(self):
        # 多进程保护机制，防止在多进程环境下重复执行
        if self._is_duplicate_process():
            return

        def run():
            pass

        task = Thread(target=run)
        task.start()

    def _is_duplicate_process(self):
        """
        检查是否为重复进程，防止在多进程环境下重复执行
        """
        # 检查是否为重载进程
        run_main = os.environ.get('RUN_MAIN', None)
        if run_main != 'true':
            return True
            
        # 检查DJANGO环境变量
        django_settings = os.environ.get('DJANGO_SETTINGS_MODULE')
        if not django_settings:
            return True
            
        return False