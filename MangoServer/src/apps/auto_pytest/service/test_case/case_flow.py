# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-23 20:38
# @Author : 毛鹏
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

from django.db.models import F
from django.utils import timezone

from src.apps.auto_system.models import TestSuite, TestSuiteDetails
from src.common.enums.tools_enum import TaskEnum, TestCaseTypeEnum
from src.common.exceptions import MangoServerError
from src.common.models.system_model import ConsumerCaseModel
from src.settings import RETRY_FREQUENCY
from src.common.tools.decorator.retry import async_task_db_connection
from src.common.tools.log_collector import log


class PyCaseFlow:
    _get_case_lock = threading.Lock()

    @classmethod
    def stop(cls):
        cls.running = False

    @classmethod
    @async_task_db_connection(infinite_retry=True)
    def process_tasks(cls):
        # while cls.running:
        #     if not cls.queue.empty():
        #         case_model = cls.queue.get()
        #         cls.executor.submit(cls.execute_task, case_model)
        #     time.sleep(0.1)
        pass

    @classmethod
    @async_task_db_connection()
    def execute_task(cls, case_model: ConsumerCaseModel):
        # from src.apps.auto_pytest.service.test_case.test_case import TestCase
        # test_case = TestCase(
        #     user_id=case_model.user_id,
        #     test_suite=case_model.test_suite,
        #     test_suite_details=case_model.test_suite_details,
        # )
        # return test_case.test_case(case_model.case_id, case_model.test_env)
        pass

    @classmethod
    def add_task(cls, case_model: ConsumerCaseModel):
        # cls.queue.put(case_model)
        pass

    @classmethod
    @async_task_db_connection()
    def get_case(cls, data):
        with cls._get_case_lock:
            case_model = None
            try:
                case_model = cls.claim_case()
                if not case_model:
                    return
                cls.send_case(case_model, data.username)
            except MangoServerError as error:
                log.system.debug(f'执行器主动拉取任务失败：{error}')
                if case_model:
                    cls.mark_claim_failed(case_model.test_suite_details)
            except Exception as error:
                log.system.error(f'执行器主动拉取任务失败：{error}')
                if case_model:
                    cls.mark_claim_failed(case_model.test_suite_details)

    @classmethod
    def claim_case(cls) -> ConsumerCaseModel | None:
        test_suite_details = TestSuiteDetails.objects.filter(
            status=TaskEnum.STAY_BEGIN.value,
            retry__lt=RETRY_FREQUENCY + 1,
            type=TestCaseTypeEnum.PYTEST.value
        ).order_by('id').first()
        if not test_suite_details:
            return None

        now = timezone.now()
        updated = TestSuiteDetails.objects.filter(
            id=test_suite_details.id,
            status=TaskEnum.STAY_BEGIN.value,
            retry__lt=RETRY_FREQUENCY + 1,
            type=TestCaseTypeEnum.PYTEST.value
        ).update(
            status=TaskEnum.PROCEED.value,
            retry=F('retry') + 1,
            push_time=now,
            update_time=now
        )
        if updated != 1:
            return None

        test_suite = TestSuite.objects.get(id=test_suite_details.test_suite_id)
        TestSuite.objects.filter(id=test_suite.id).update(status=TaskEnum.PROCEED.value, update_time=now)
        return ConsumerCaseModel(
            test_suite_details=test_suite_details.id,
            test_suite=test_suite_details.test_suite_id,
            case_id=test_suite_details.case_id,
            case_name=test_suite_details.case_name,
            test_env=test_suite_details.test_env,
            user_id=test_suite.user_id,
            tasks_id=test_suite.tasks_id,
            parametrize=test_suite_details.parametrize,
        )

    @classmethod
    def mark_claim_failed(cls, test_suite_details_id: int):
        TestSuiteDetails.objects.filter(id=test_suite_details_id).update(
            status=TaskEnum.FAIL.value,
            update_time=timezone.now()
        )

    @classmethod
    def send_case(cls, case_model, send_case_user):
        from src.apps.auto_pytest.service.test_case.test_case import TestCase
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
