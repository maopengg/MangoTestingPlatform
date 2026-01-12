from threading import Thread

import atexit
import time
from django.apps import AppConfig

from src.tools import is_main_process
from src.tools.log_collector import log


class AutoApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_api'
    _health_check_thread = None
    _health_check_running = False

    def ready(self):
        # 多进程保护机制，防止在多进程环境下重复执行
        if is_main_process():
            return

        def run():
            try:
                time.sleep(10)
                self.test_case_consumption()
                # 启动健康检查线程
                self._start_health_check()
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

    def _start_health_check(self):
        """启动健康检查线程，定期检查消费线程是否还在运行"""
        if AutoApiConfig._health_check_running:
            return

        AutoApiConfig._health_check_running = True

        def health_check():
            from src.auto_test.auto_api.service.test_case.case_flow import ApiCaseFlow
            while AutoApiConfig._health_check_running:
                try:
                    time.sleep(60)  # 每分钟检查一次
                    # 检查线程是否还在运行
                    if not ApiCaseFlow.running:
                        log.api.info('API任务获取线程已被标记为停止，健康检查退出')
                        break

                    if ApiCaseFlow.thread is None or not ApiCaseFlow.thread.is_alive():
                        log.api.warning('检测到API任务获取线程已退出，尝试自动重启...')
                        try:
                            ApiCaseFlow.start()
                            log.api.info('API任务获取线程已自动重启')
                        except Exception as e:
                            log.api.error(f'自动重启API任务获取线程失败: {e}')
                            import traceback
                            log.api.info(f'详细错误信息: {traceback.format_exc()}')
                except (RuntimeError, SystemError) as e:
                    error_msg = str(e).lower()
                    if any(keyword in error_msg for keyword in
                           ['shutdown', 'interpreter', 'cannot schedule', 'after shutdown']):
                        log.api.info('健康检查线程：忽略进程关闭错误')
                        break
                    log.api.info(f'健康检查线程出错: {e}')
                    time.sleep(10)
                except Exception as e:
                    log.api.info(f'健康检查线程异常: {e}')
                    import traceback
                    log.api.info(f'详细错误信息: {traceback.format_exc()}')
                    time.sleep(10)

        AutoApiConfig._health_check_thread = Thread(target=health_check, daemon=True, name='AutoApiConfig-HealthCheck')
        AutoApiConfig._health_check_thread.start()
        log.api.info('API任务健康检查线程已启动')

    def shutdown(self):
        AutoApiConfig._health_check_running = False
        from src.auto_test.auto_api.service.test_case.case_flow import ApiCaseFlow
        ApiCaseFlow.stop()
