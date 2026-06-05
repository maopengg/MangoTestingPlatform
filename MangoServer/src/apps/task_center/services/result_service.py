from django.utils import timezone

from src.apps.auto_system.models import TestSuite, TestSuiteDetails
from src.common.enums.tools_enum import TaskEnum
from src.apps.task_center.enums import ScheduleFireStatusEnum
from src.apps.task_center.models import ScheduleFire


class ScheduleFireResultService:
    @classmethod
    def refresh_by_test_suite(cls, test_suite_id: int):
        has_running_detail = TestSuiteDetails.objects.filter(
            test_suite_id=test_suite_id,
            status__in=[TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value],
        ).exists()
        if has_running_detail:
            return
        test_suite = TestSuite.objects.filter(id=test_suite_id).first()
        status = ScheduleFireStatusEnum.SUCCESS.value
        if test_suite and test_suite.status == TaskEnum.FAIL.value:
            status = ScheduleFireStatusEnum.FAIL.value
        ScheduleFire.objects.filter(test_suite_id=test_suite_id).update(
            status=status,
            update_time=timezone.now(),
        )
