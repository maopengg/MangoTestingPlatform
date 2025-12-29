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
from src.tools.decorator.retry import async_task_db_connection
from src.tools.log_collector import log


class ApiCaseFlow:
    max_tasks = 10
    executor = ThreadPoolExecutor(max_workers=max_tasks)
    _get_case_lock = threading.Lock()
    retry_frequency = 3
    running = True
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
                cls.get_case()
                time.sleep(0.5)  # 短暂休眠避免过度轮询
            except Exception as e:
                log.system.error(f'API任务获取器出错: {e}')
                time.sleep(2)  # 出错时增加休眠时间

    @classmethod
    @async_task_db_connection(max_retries=3, retry_delay=2)
    def get_case(cls, ):
        with cls._get_case_lock:
            if cls._active_tasks > cls.max_tasks:
                return
            test_suite_details = TestSuiteDetails.objects.filter(
                status=TaskEnum.STAY_BEGIN.value,
                retry__lt=cls.retry_frequency + 1,
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
                    log.system.debug(f'API发送用例：{case_model.model_dump_json()}')
                    future = cls.executor.submit(cls.execute_task, case_model)
                    cls._active_tasks += 1
                    cls.update_status_proceed(test_suite, test_suite_details)

                    def task_done(fut):
                        with cls._get_case_lock:
                            cls._active_tasks = max(0, cls._active_tasks - 1)

                    future.add_done_callback(task_done)
            except Exception as error:
                log.system.error(f'执行器主动拉取任务失败：{error}')
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
