# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-23 20:38
# @Author : 毛鹏
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

from django.utils import timezone

from src.enums.tools_enum import TaskEnum, TestCaseTypeEnum
from src.exceptions import MangoServerError
from src.models.system_model import ConsumerCaseModel
from src.tools.decorator.retry import ensure_db_connection
from src.tools.log_collector import log


class PyCaseFlow:
    queue = Queue()
    max_tasks = 2
    executor = ThreadPoolExecutor(max_workers=max_tasks)
    running = True
    _get_case_lock = threading.Lock()
    retry_frequency = 3

    @classmethod
    def stop(cls):
        cls.running = False

    @classmethod
    @ensure_db_connection(True)
    def process_tasks(cls):
        while cls.running:
            if not cls.queue.empty():
                case_model = cls.queue.get()
                cls.executor.submit(cls.execute_task, case_model)
            time.sleep(0.1)

    @classmethod
    @ensure_db_connection()
    def execute_task(cls, case_model: ConsumerCaseModel):
        from src.auto_test.auto_pytest.service.test_case.test_case import TestCase
        test_case = TestCase(
            user_id=case_model.user_id,
            test_suite=case_model.test_suite,
            test_suite_details=case_model.test_suite_details,
        )
        return test_case.test_case(case_model.case_id, case_model.test_env)

    @classmethod
    def add_task(cls, case_model: ConsumerCaseModel):
        cls.queue.put(case_model)

    @classmethod
    def get_case(cls, data):
        from src.auto_test.auto_system.models import TestSuite, TestSuiteDetails
        with cls._get_case_lock:
            test_suite_details = TestSuiteDetails.objects.filter(
                status=TaskEnum.STAY_BEGIN.value,
                retry__lt=cls.retry_frequency + 1,
                type=TestCaseTypeEnum.UI.value
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
                    cls.send_case(case_model, data.username)
                    cls.update_status_proceed(test_suite, test_suite_details)
            except MangoServerError as error:
                log.system.debug(f'执行器主动拉取任务失败：{error}')
                test_suite_details.status = TaskEnum.FAIL.value
                test_suite_details.save()

    @classmethod
    def send_case(cls, case_model, send_case_user):
        from src.auto_test.auto_pytest.service.test_case.test_case import TestCase
        send_case = TestCase(
            user_id=send_case_user,
            test_suite=case_model.test_suite,
            test_suite_details=case_model.test_suite_details,
        )
        send_case.test_case(
            case_id=case_model.case_id,
            test_env=case_model.test_env,
        )

    @classmethod
    def update_status_proceed(cls, test_suite, test_suite_details):
        test_suite.status = TaskEnum.PROCEED.value
        test_suite.save()

        test_suite_details.status = TaskEnum.PROCEED.value
        test_suite_details.retry += 1
        test_suite_details.push_time = timezone.now()
        test_suite_details.save()
