# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-11-23 20:38
# @Author : 毛鹏
import threading

from django.db.models import F
from django.utils import timezone
from mangotools.contracts import TaskPullRequest
from mangotools.enums import TaskEnum

from src.apps.system.services.system_config import SystemConfigService
from src.apps.task_center.schemas.execution import ExecutionCaseCommand
from src.apps.task_center.services.execution.actuator_task_lease import ActuatorTaskLease
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.user.models import User
from src.common.logging import log


class UiCaseFlow:
    current_index = 0
    _get_case_lock = threading.Lock()

    @classmethod
    def execute_task(cls, case_model: ExecutionCaseCommand, retry=0, max_retry=3):
        # retry += 1
        #     return
        # try:
        #     cls.current_index = (cls.current_index + 1) % len(user_list)
        #     user = user_list[cls.current_index]
        # except IndexError:
        #     time.sleep(3)
        #     return cls.execute_task(case_model, retry, max_retry)
        # cls.send_case(user.user_id, user.username, case_model, user.username)
        pass

    @classmethod
    def add_task(cls, case_model: ExecutionCaseCommand):
        # cls.execute_task(case_model)
        pass

    @classmethod
    def get_case(cls, data: TaskPullRequest):
        model = User.objects.get(username=data.username)
        with cls._get_case_lock:
            case_model = None
            try:
                claim_result = cls.claim_case()
                if not claim_result:
                    return
                case_model, send_case_user = claim_result
                log.system.debug(
                    f'UI发送用例：case_id={case_model.case_id}，'
                    f'test_suite_details={case_model.test_suite_details}，test_env={case_model.test_env}'
                )
                cls.send_case(model.pk, model.username, case_model, send_case_user)
            except Exception as error:
                log.system.error(f'执行器主动拉取任务失败：{error}')
                if case_model:
                    cls.mark_claim_failed(case_model.test_suite_details)

    @classmethod
    def pull_cases(cls, data: TaskPullRequest, capacity: int, source_message_id: str | None = None) -> list[dict]:
        model = User.objects.get(username=data.username)
        tasks = []
        capacity = max(0, min(int(capacity or 0), 5))
        with cls._get_case_lock:
            ActuatorTaskLease.recover_expired()
            for _ in range(capacity):
                case_model = None
                try:
                    claim_result = cls.claim_case()
                    if not claim_result:
                        break
                    case_model, send_case_user = claim_result
                    from src.apps.auto_ui.services.test_case.test_case import TestCase
                    send_case = TestCase(
                        user_id=model.pk,
                        username=model.username,
                        test_env=case_model.test_env,
                        tasks_id=case_model.tasks_id,
                        is_send=False
                    )
                    payload = send_case.test_case(
                        case_id=case_model.case_id,
                        case_name=case_model.case_name,
                        test_suite=case_model.test_suite,
                        test_suite_details=case_model.test_suite_details,
                        parametrize=case_model.parametrize,
                        send_case_user=send_case_user
                    )
                    dispatch_id = f'ui:{case_model.test_suite_details}'
                    ActuatorTaskLease.set_lease(
                        case_model.test_suite_details,
                        source_message_id,
                        data.username,
                        dispatch_id,
                    )
                    tasks.append({
                        'dispatch_id': dispatch_id,
                        'source_message_id': source_message_id,
                        'task_type': 'ui',
                        'case_id': case_model.case_id,
                        'case_name': case_model.case_name,
                        'send_user': send_case_user,
                        'payload': payload.model_dump(mode='json'),
                    })
                except Exception as error:
                    log.system.error(f'执行器HTTP拉取UI任务失败：{error}')
                    if case_model:
                        cls.mark_claim_failed(case_model.test_suite_details)
        return tasks

    @classmethod
    def claim_case(cls) -> tuple[ExecutionCaseCommand, str] | None:
        max_attempts = SystemConfigService.get_test_suite_timeout_max_attempts()
        test_suite_details = TestSuiteDetails.objects.filter(
            status=TaskEnum.STAY_BEGIN.value,
            retry__lt=max_attempts,
            type=TestCaseTypeEnum.UI.value
        ).alias(
            execution_priority=TestCenterQuerySelector.execution_environment_priority(),
        ).order_by('execution_priority', 'create_time').first()
        if not test_suite_details:
            return None

        now = timezone.now()
        updated = TestSuiteDetails.objects.filter(
            id=test_suite_details.id,
            status=TaskEnum.STAY_BEGIN.value,
            retry__lt=max_attempts,
            type=TestCaseTypeEnum.UI.value
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
        ), test_suite.user.username

    @classmethod
    def mark_claim_failed(cls, test_suite_details_id: int):
        TestSuiteDetails.objects.filter(id=test_suite_details_id).update(
            status=TaskEnum.FAIL.value,
            update_time=timezone.now()
        )

    @classmethod
    def update_status_proceed(cls, test_suite, test_suite_details):
        test_suite.status = TaskEnum.PROCEED.value
        test_suite.save()

        test_suite_details.status = TaskEnum.PROCEED.value
        test_suite_details.retry += 1
        test_suite_details.push_time = timezone.now()
        test_suite_details.save()

    @classmethod
    def send_case(cls, user_id, username, case_model, send_case_user):
        from src.apps.auto_ui.services.test_case.test_case import TestCase
        send_case = TestCase(
            user_id=user_id,
            username=username,
            test_env=case_model.test_env,
            tasks_id=case_model.tasks_id,
            is_send=True
        )
        send_case.test_case(
            case_id=case_model.case_id,
            case_name=case_model.case_name,
            test_suite=case_model.test_suite,
            test_suite_details=case_model.test_suite_details,
            parametrize=case_model.parametrize,
            send_case_user=send_case_user
        )
