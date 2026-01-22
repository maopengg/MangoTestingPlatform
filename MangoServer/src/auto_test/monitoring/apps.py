# -*- coding: utf-8 -*-
# @Description: 预警监控 APP 配置
import os
import threading
import time
import atexit
from django.apps import AppConfig

from src.tools.log_collector import log
from src.tools import is_main_process


class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.monitoring'

    def ready(self):
        """
        服务启动时恢复任务
        """

        # 多进程保护机制，防止在多进程环境下重复执行
        if is_main_process(lock_name='mango_monitoring_init', logger=log.monitoring):
            return


        def run():
            try:
                # 延迟执行，确保数据库连接已建立
                # 开发模式下延迟更长时间，避免重载时的问题
                import sys
                delay = 10 if ('runserver' in sys.argv or 'runserver_plus' in sys.argv) else 5
                time.sleep(delay)
                log.monitoring.info('监控模块：开始执行任务恢复')
                self.restore_tasks()
            except RuntimeError as e:
                # 忽略进程关闭时的错误（开发服务器重载时常见）
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ['shutdown', 'interpreter', 'cannot schedule', 'after shutdown']):
                    # 开发模式下这些错误是正常的，静默忽略
                    log.monitoring.debug(f'监控模块：忽略进程关闭错误: {e}')
                    return
                log.monitoring.error(f'恢复监控任务状态异常: {e}')
            except Exception as e:
                # 其他异常记录日志但不影响启动
                log.monitoring.error(f'恢复监控任务状态异常: {e}')
                import traceback
                traceback.print_exc()

        task = threading.Thread(target=run, daemon=True)
        task.start()
        # 只在主进程中注册退出处理函数，避免在开发服务器重载时被意外触发
        # 使用模块级别的标志确保只注册一次
        if not hasattr(MonitoringConfig, '_shutdown_registered'):
            atexit.register(self.shutdown)
            MonitoringConfig._shutdown_registered = True


    @staticmethod
    def restore_tasks():
        """
        恢复任务
        """
        try:
            log.monitoring.info('监控模块：开始执行任务恢复...')
            from src.auto_test.monitoring.service.runner import restore_running_tasks
            restore_running_tasks()
            log.monitoring.info('监控模块：任务恢复完成')
        except Exception as e:
            log.monitoring.error(f'恢复监控任务状态异常: {e}')
            import traceback
            traceback.print_exc()

    def shutdown(self):
        """
        停止所有监控任务
        """
        try:
            from src.auto_test.monitoring.service.runner import stop_all_tasks
            stop_all_tasks(timeout=5.0)
            log.monitoring.info('监控模块已终止所有任务进程，状态保持不变以便重启时恢复')
        except Exception as e:
            log.monitoring.error(f'停止监控任务时发生异常: {e}')
            import traceback
            traceback.print_exc()

