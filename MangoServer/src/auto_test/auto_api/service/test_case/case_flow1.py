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
    thread = None

    @classmethod
    def start(cls):
        """启动后台任务获取线程"""
        if cls.thread is not None and cls.thread.is_alive():
            log.api.info('API任务获取线程已在运行，跳过重复启动')
            return
        cls.thread = threading.Thread(target=cls._background_task_fetcher, daemon=True)
        cls.thread.start()
        log.api.info('API任务获取线程已启动')

    @classmethod
    def _background_task_fetcher(cls):
        """后台任务获取循环"""
        log.api.info('API用例执行启动成功！')
        while True:
            try:
                cls.executor.submit(cls.get_case, )
                time.sleep(0.5)
            except Exception as e:
                log.api.info(f'API任务获取器出错: {str(e)}, 类型: {type(e).__name__}')
                import traceback
                log.api.info(f'详细错误信息: {traceback.format_exc()}')

    @classmethod
    @async_task_db_connection(max_retries=1, retry_delay=1)
    def get_case(cls, ):
        with cls._get_case_lock:
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
                    cls.execute_task(case_model)
                    cls.update_status_proceed(test_suite, test_suite_details)

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
