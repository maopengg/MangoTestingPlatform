from threading import Thread

import time
import os
from django.apps import AppConfig

from src.tools.log_collector import log
from src.tools import is_main_process


class AutoPytestConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_pytest'

    def ready(self):
        # 多进程保护机制，防止在多进程环境下重复执行
        if is_main_process():
            return

        def run():
            try:
                time.sleep(10)
                self.pull_code()
            except (RuntimeError, SystemError) as e:
                # 忽略进程关闭时的错误（开发服务器重载时常见）
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ['shutdown', 'interpreter', 'cannot schedule', 'after shutdown']):
                    log.pytest.debug(f'Pytest模块：忽略进程关闭错误: {e}')
                    return
                raise
            except Exception as e:
                import traceback
                log.pytest.error(f'异常提示:{e}, 首次启动项目，请启动完成之后再重启一次！')
                traceback.print_exc()

        # 设置为 daemon 线程，确保在服务关闭时能够快速退出
        task = Thread(target=run, daemon=True)
        task.start()


    def pull_code(self):
        from src.auto_test.auto_pytest.service.base import git_obj
        try:
            git_obj()
        except Exception as e:
            import traceback
            log.pytest.error(f'异常提示:{e}, 首次启动项目，请启动完成之后再重启一次！')
            log.pytest.info(f'如果您的项目已经配置了pytest等相关配置则关注下这个异常，如果没有配置请忽略！')