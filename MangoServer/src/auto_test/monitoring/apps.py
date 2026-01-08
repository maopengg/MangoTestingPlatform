# -*- coding: utf-8 -*-
# @Description: 预警监控 APP 配置
import os
import threading
import time
import atexit
from django.apps import AppConfig

from src.tools.log_collector import log


class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.monitoring'

    def ready(self):
        """
        服务启动时恢复任务状态
        """
        log.system.info('监控模块：ready() 方法被调用')
        
        # 多进程保护机制，防止在多进程环境下重复执行
        if self._is_duplicate_process():
            log.system.info('监控模块：检测到重复进程，跳过初始化')
            return

        log.system.info('监控模块：准备启动恢复任务的后台线程')

        def run():
            try:
                # 延迟执行，确保数据库连接已建立
                # 开发模式下延迟更长时间，避免重载时的问题
                import sys
                delay = 10 if ('runserver' in sys.argv or 'runserver_plus' in sys.argv) else 5
                log.system.info(f'监控模块：后台线程启动，将在 {delay} 秒后执行任务恢复')
                time.sleep(delay)
                
                log.system.info('监控模块：延迟时间已到，开始检查进程状态')
                
                # 再次检查进程是否还在运行（开发模式下重载时可能已经关闭）
                # 注意：延迟后不应该再检查重复进程，因为此时已经是主进程了
                # 如果再次检查，可能会因为锁文件等原因误判
                # 所以这里注释掉重复检查，直接执行恢复逻辑
                # if self._is_duplicate_process():
                #     log.system.info('监控模块：延迟后检测到重复进程，跳过任务恢复')
                #     return
                
                log.system.info('监控模块：开始执行任务恢复')
                self.restore_tasks()
            except (RuntimeError, SystemError) as e:
                # 忽略进程关闭时的错误（开发服务器重载时常见）
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ['shutdown', 'interpreter', 'cannot schedule', 'after shutdown']):
                    # 开发模式下这些错误是正常的，静默忽略
                    log.system.debug(f'监控模块：忽略进程关闭错误: {e}')
                    return
                log.system.error(f'恢复监控任务状态异常: {e}')
            except Exception as e:
                # 其他异常记录日志但不影响启动
                log.system.error(f'恢复监控任务状态异常: {e}')
                import traceback
                traceback.print_exc()

        # 启动后台任务（daemon 线程，进程退出时自动终止）
        task = threading.Thread(target=run, daemon=True)
        task.start()
        log.system.info('监控模块：后台线程已启动')
        
        # 注册退出时的清理函数（同步停止所有监控任务）
        atexit.register(self.shutdown)
        log.system.info('监控模块：已注册退出清理函数')

    def _is_duplicate_process(self):
        """
        检查是否为重复进程，防止在多进程环境下重复执行
        """
        # 获取当前进程ID
        pid = os.getpid()

        # 检查是否为重载进程
        run_main = os.environ.get('RUN_MAIN', None)
        if run_main != 'true':
            log.system.debug(f"【监控模块】跳过重复进程初始化 - PID: {pid}, RUN_MAIN: {run_main}")
            return True

        # 检查DJANGO环境变量
        django_settings = os.environ.get('DJANGO_SETTINGS_MODULE')
        if not django_settings:
            log.system.debug(f"【监控模块】跳过重复进程初始化 - PID: {pid}, DJANGO_SETTINGS_MODULE未设置")
            return True

        # 在Docker环境下，使用文件锁机制防止重复执行
        # 兼容Windows和Linux系统
        if os.name == 'nt':  # Windows系统
            temp_dir = os.environ.get('TEMP', os.environ.get('TMP', 'C:\\temp'))
            lock_file = f"{temp_dir}\\mango_monitoring_init_{os.getppid()}.lock"
        else:  # Linux/Unix系统
            lock_file = f"/tmp/mango_monitoring_init_{os.getppid()}.lock"
        try:
            # 尝试创建锁文件
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL)
            os.close(fd)
            # 注册退出时清理锁文件
            import atexit
            atexit.register(lambda: os.path.exists(lock_file) and os.remove(lock_file))
            log.system.debug(f"监控模块主进程初始化 - PID: {pid}")
            return False
        except FileExistsError:
            log.system.debug(f"【监控模块】跳过重复进程初始化 - PID: {pid}, 锁文件已存在")
            return True
        except Exception as e:
            # 如果无法创建锁文件（如权限问题），使用备用方法
            log.system.debug(f"锁文件检查异常 - PID: {pid}, 错误: {e}")
            # 检查父进程ID，避免在子进程中重复执行
            ppid = os.getppid()
            if hasattr(self, '_initialized_ppid') and self._initialized_ppid == ppid:
                return True
            self._initialized_ppid = ppid
            return False

    @staticmethod
    def restore_tasks():
        """
        恢复任务状态
        """
        try:
            log.system.info('监控模块：开始执行任务恢复...')
            from src.auto_test.monitoring.service.runner import restore_running_tasks
            restore_running_tasks()
            log.system.info('监控模块：任务恢复完成')
        except Exception as e:
            log.system.error(f'恢复监控任务状态异常: {e}')
            import traceback
            traceback.print_exc()

    def shutdown(self):
        """
        服务停止时的清理函数
        同步停止所有正在运行的监控任务子进程
        """
        try:
            from src.auto_test.monitoring.service.runner import stop_all_tasks
            stop_all_tasks(timeout=5.0)
            log.system.info('监控模块已停止所有任务')
        except Exception as e:
            log.system.error(f'停止监控任务时发生异常: {e}')
            import traceback
            traceback.print_exc()

