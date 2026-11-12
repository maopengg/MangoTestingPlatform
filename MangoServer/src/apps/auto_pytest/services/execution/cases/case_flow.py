# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-11-23 20:38
# @Author : 毛鹏
import threading

from django.db.models import F
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.system.services.configuration.system_config import SystemConfigService
from src.apps.task_center.schemas.execution import ExecutionCaseCommand
from src.apps.task_center.services.execution.actuator_task_lease import ActuatorTaskLease
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.common.decorators.retry import async_task_db_connection
from src.common.exceptions import MangoServerError
from src.common.logging import log


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
    def execute_task(cls, case_model: ExecutionCaseCommand):
        # from src.apps.auto_pytest.services.execution.cases.test_case import TestCase
        # test_case = TestCase(
        #     user_id=case_model.user_id,
        #     test_suite=case_model.test_suite,
        #     test_suite_details=case_model.test_suite_details,
        # )
        # return test_case.test_case(case_model.case_id, case_model.test_env)
        pass

    @classmethod
    def add_task(cls, case_model: ExecutionCaseCommand):
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
    def pull_cases(cls, data, capacity: int, source_message_id: str | None = None) -> list[dict]:
        tasks = []
        capacity = max(0, min(int(capacity or 0), 5))
        with cls._get_case_lock:
            ActuatorTaskLease.recover_expired()
            for _ in range(capacity):
                case_model = None
                try:
                    case_model = cls.claim_case()
                    if not case_model:
                        break
                    from src.apps.auto_pytest.services.execution.cases.test_case import TestCase
                    send_case = TestCase(
                        user_id=data.username,
                        test_suite=case_model.test_suite,
                        test_suite_details=case_model.test_suite_details,
                        is_send=False,
                    )
                    payload = send_case.test_case(
                        case_id=case_model.case_id,
                        test_env=case_model.test_env,
                    )
                    dispatch_id = f'pytest:{case_model.test_suite_details}'
                    ActuatorTaskLease.set_lease(
                        case_model.test_suite_details,
                        source_message_id,
                        data.username,
                        dispatch_id,
                    )
                    tasks.append({
                        'dispatch_id': dispatch_id,
                        'source_message_id': source_message_id,
                        'task_type': 'pytest',
                        'case_id': case_model.case_id,
                        'case_name': case_model.case_name,
                        'send_user': data.username,
                        'payload': payload,
                    })
                except MangoServerError as error:
                    log.system.debug(f'执行器HTTP拉取Pytest任务失败：{error}')
                    if case_model:
                        cls.mark_claim_failed(case_model.test_suite_details)
                except Exception as error:
                    log.system.error(f'执行器HTTP拉取Pytest任务失败：{error}')
                    if case_model:
                        cls.mark_claim_failed(case_model.test_suite_details)
        return tasks

    @classmethod
    def claim_case(cls) -> ExecutionCaseCommand | None:
        max_attempts = SystemConfigService.get_test_suite_timeout_max_attempts()
        test_suite_details = TestSuiteDetails.objects.filter(
            status=TaskEnum.STAY_BEGIN.value,
            retry__lt=max_attempts,
            type=TestCaseTypeEnum.PYTEST.value
        ).order_by('id').first()
        if not test_suite_details:
            return None

        now = timezone.now()
        updated = TestSuiteDetails.objects.filter(
            id=test_suite_details.id,
            status=TaskEnum.STAY_BEGIN.value,
            retry__lt=max_attempts,
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
        return ExecutionCaseCommand(
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
        from src.apps.auto_pytest.services.execution.cases.test_case import TestCase
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
