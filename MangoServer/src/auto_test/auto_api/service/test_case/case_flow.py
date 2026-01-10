# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-23 20:38
# @Author : 毛鹏
import threading
from concurrent.futures import ThreadPoolExecutor

import time
from django.utils import timezone

from src.auto_test.auto_system.models import TestSuite, TestSuiteDetails
from src.enums.tools_enum import TaskEnum, TestCaseTypeEnum
from src.models.system_model import ConsumerCaseModel
from src.settings import API_MAX_TASKS, RETRY_FREQUENCY
from src.tools.decorator.retry import async_task_db_connection
from src.tools.log_collector import log


class ApiCaseFlow:
    executor = ThreadPoolExecutor(max_workers=API_MAX_TASKS)
    _get_case_lock = threading.Lock()
    running = True
    _active_tasks = 0
    thread = None
    _thread_lock = threading.Lock()

    @classmethod
    def start(cls):
        """启动后台任务获取线程"""
        with cls._thread_lock:
            # 检查线程是否已经存在且正在运行
            if cls.thread is not None and cls.thread.is_alive():
                log.api.info('API任务获取线程已在运行，跳过重复启动')
                return

            # 确保 running 标志为 True
            cls.running = True
            cls.thread = threading.Thread(target=cls._background_task_fetcher, daemon=True, name='ApiCaseFlow-Fetcher')
            cls.thread.start()
            log.api.info('API任务获取线程已启动')

    @classmethod
    def stop(cls):
        """停止后台任务获取"""
        with cls._thread_lock:
            cls.running = False
        try:
            # 不等待，快速关闭，避免在服务器关闭时阻塞
            cls.executor.shutdown(wait=False)
        except (RuntimeError, SystemError) as e:
            # 忽略关闭时的正常错误
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in
                   ['shutdown', 'interpreter', 'cannot schedule', 'after shutdown']):
                return
            log.system.debug(f'停止API任务执行器时忽略错误: {e}')
        except Exception as e:
            log.api.info(f'停止API任务执行器异常: {e}')

    @classmethod
    def _background_task_fetcher(cls):
        """后台任务获取循环"""
        log.api.info('API用例执行启动成功！')
        consecutive_errors = 0
        max_consecutive_errors = 10  # 连续错误超过10次才考虑重启

        while cls.running:
            try:
                cls.get_case()
                consecutive_errors = 0  # 成功执行，重置错误计数
                time.sleep(0.5)
            except (RuntimeError, SystemError) as e:
                # 忽略进程关闭时的错误（开发服务器重载时常见）
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in
                       ['shutdown', 'interpreter', 'cannot schedule', 'after shutdown']):
                    log.api.info(f'API任务获取器：忽略进程关闭错误: {e}')
                    break
                consecutive_errors += 1
                log.api.info(f'API任务获取器出错（连续{consecutive_errors}次）: {e}')
                # 如果连续错误太多，等待更长时间
                sleep_time = min(2 * consecutive_errors, 30)  # 最多等待30秒
                time.sleep(sleep_time)
            except Exception as e:
                consecutive_errors += 1
                log.api.info(f'API任务获取器出错（连续{consecutive_errors}次）: {str(e)}, 类型: {type(e).__name__}')
                import traceback
                log.api.info(f'详细错误信息: {traceback.format_exc()}')
                # 如果连续错误太多，等待更长时间，但不要退出线程
                sleep_time = min(2 * consecutive_errors, 30)  # 最多等待30秒
                time.sleep(sleep_time)

            # 如果连续错误太多，记录警告但继续运行（不要退出线程）
            if consecutive_errors >= max_consecutive_errors:
                log.api.info(f'API任务获取器连续出错{consecutive_errors}次，但将继续尝试...')
                consecutive_errors = 0  # 重置计数，继续尝试

        log.api.info('API任务获取循环已退出')

    @classmethod
    @async_task_db_connection()
    def get_case(cls, ):
        with cls._get_case_lock:
            if cls._active_tasks > API_MAX_TASKS:
                return
            test_suite_details = TestSuiteDetails.objects.filter(
                status=TaskEnum.STAY_BEGIN.value,
                retry__lt=RETRY_FREQUENCY + 1,
                type=TestCaseTypeEnum.API.value
            ).first()
            if test_suite_details:
                try:
                    test_suite = TestSuite.objects.get(id=test_suite_details.test_suite.id)
                    case_model = ConsumerCaseModel(
                        test_suite_details=test_suite_details.id,
                        test_suite=test_suite_details.test_suite.id,
                        case_id=test_suite_details.case_id,
                        case_name=test_suite_details.case_name,
                        test_env=test_suite_details.test_env,
                        user_id=test_suite.user.id,
                        tasks_id=test_suite.tasks.id if test_suite.tasks else None,
                        parametrize=test_suite_details.parametrize,
                    )
                    log.api.info(f'API发送用例：{case_model.model_dump_json()}')
                    future = cls.executor.submit(cls.execute_task, case_model)
                    cls._active_tasks += 1
                    cls.update_status_proceed(test_suite, test_suite_details)

                    def task_done(fut):
                        with cls._get_case_lock:
                            cls._active_tasks = max(0, cls._active_tasks - 1)

                    future.add_done_callback(task_done)
                except Exception as error:
                    log.api.info(f'执行器主动拉取任务失败：{error}')
                    test_suite_details.status = TaskEnum.FAIL.value
                    test_suite_details.retry += 1
                    test_suite_details.save()

    @classmethod
    def execute_task(cls, case_model: ConsumerCaseModel):
        from src.auto_test.auto_api.service.test_case.test_case import TestCase
        test_case = TestCase(
            user_id=case_model.user_id,
            test_env=case_model.test_env,
            case_id=case_model.case_id,
            test_suite=case_model.test_suite,
            test_suite_details=case_model.test_suite_details,
        )
        return test_case.test_case()

    @classmethod
    def update_status_proceed(cls, test_suite, test_suite_details):
        test_suite.status = TaskEnum.PROCEED.value
        test_suite.save()

        test_suite_details.status = TaskEnum.PROCEED.value
        test_suite_details.retry += 1
        test_suite_details.push_time = timezone.now()
        test_suite_details.save()

    @classmethod
    def add_task(cls, case_model: ConsumerCaseModel):
        pass
