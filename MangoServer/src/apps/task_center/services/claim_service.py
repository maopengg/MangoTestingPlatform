from datetime import timedelta

from django.db.models import F, Q
from django.utils import timezone

from src.apps.auto_system.models import TestSuite, TestSuiteDetails
from src.common.enums.tools_enum import TaskEnum, TestCaseTypeEnum
from src.common.models.system_model import ConsumerCaseModel
from src.settings import RETRY_FREQUENCY


class ApiTaskClaimService:
    @classmethod
    def claim(cls, lease_seconds: int = 1800) -> ConsumerCaseModel | None:
        now = timezone.now()
        timeout_at = now - timedelta(seconds=lease_seconds)
        detail = TestSuiteDetails.objects.filter(
            Q(status=TaskEnum.STAY_BEGIN.value) | Q(status=TaskEnum.PROCEED.value, push_time__lt=timeout_at),
            retry__lt=RETRY_FREQUENCY + 1,
            type=TestCaseTypeEnum.API.value,
        ).order_by('id').first()
        if not detail:
            return None
        updated = TestSuiteDetails.objects.filter(
            Q(status=TaskEnum.STAY_BEGIN.value) | Q(status=TaskEnum.PROCEED.value, push_time__lt=timeout_at),
            id=detail.id,
            retry__lt=RETRY_FREQUENCY + 1,
            type=TestCaseTypeEnum.API.value,
        ).update(
            status=TaskEnum.PROCEED.value,
            retry=F('retry') + 1,
            push_time=now,
            update_time=now,
        )
        if updated != 1:
            return None
        test_suite = TestSuite.objects.get(id=detail.test_suite_id)
        TestSuite.objects.filter(id=test_suite.id).update(status=TaskEnum.PROCEED.value, update_time=now)
        return ConsumerCaseModel(
            test_suite_details=detail.id,
            test_suite=detail.test_suite_id,
            case_id=detail.case_id,
            case_name=detail.case_name,
            test_env=detail.test_env,
            user_id=test_suite.user_id,
            tasks_id=test_suite.tasks_id,
            parametrize=detail.parametrize,
        )

