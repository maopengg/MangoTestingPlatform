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
    _get_case_lock1 = threading.Lock()
    running = True
    # 用于跟踪当前活跃的任务数
    _active_tasks = 0

    @classmethod
    def start(cls):
        """启动后台任务获取线程"""
        thread = threading.Thread(target=cls._background_task_fetcher)
        thread.daemon = True
        thread.start()

    @classmethod
    def stop(cls):
        """停止后台任务获取"""
        cls.running = False
        cls.executor.shutdown(wait=True)  # 关闭线程池

    @classmethod
    def _background_task_fetcher(cls):
        """后台任务获取循环"""
        while cls.running:
            try:
                # log.api.info(f'当前线程池：{cls._active_tasks}，最大：{API_MAX_TASKS}')
                if cls._active_tasks > API_MAX_TASKS:
                    time.sleep(3)  # 短暂休眠避免过度轮询
                else:
                    cls.get_case()
            except Exception as e:
                log.api.error(f'API任务获取器出错: {e}')
                time.sleep(2)  # 出错时增加休眠时间

    @classmethod
    @async_task_db_connection(max_retries=3, retry_delay=2)
    def get_case(cls, ):
        with cls._get_case_lock:

            test_suite_details = TestSuiteDetails.objects.filter(
                status=TaskEnum.STAY_BEGIN.value,
                retry__lt=RETRY_FREQUENCY + 1,
                type=TestCaseTypeEnum.API.value
            ).first()
            try:
                if test_suite_details:
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
                    log.api.debug(f'API发送用例：{case_model.model_dump_json()}')
                    # 提交任务到线程池执行
                    future = cls.executor.submit(cls.execute_task, case_model)
                    # 增加活跃任务计数
                    cls._active_tasks += 1
                    cls.update_status_proceed(test_suite, test_suite_details)

                    # 添加回调，在任务完成后减少计数
                    def task_done(fut):
                        # 在回调函数中也需要使用锁来保证线程安全
                        with cls._get_case_lock1:
                            cls._active_tasks = max(0, cls._active_tasks - 1)

                    future.add_done_callback(task_done)
            except Exception as error:
                log.api.error(f'执行器主动拉取任务失败：{error}')
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
        # API任务现在完全通过数据库队列管理
        # 不需要做任何特殊处理，后台任务获取器会自动获取待执行的任务
        # 任务状态已经在add_test_suite_details中设置为STAY_BEGIN
        pass
