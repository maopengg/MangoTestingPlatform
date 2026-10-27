from django.db import transaction

from mangotools.enums import TaskEnum
from src.apps.test_center.enums import ReportFailureReasonEnum
from src.apps.test_center.exceptions import (
    TestCenterError, TEST_REPORT_NOT_FOUND, TEST_REPORT_DISPOSITION_INVALID,
    TEST_REPORT_DISPOSITION_ACTIVE, TEST_REPORT_EXCLUSION_NOT_FAILED,
)
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.common.exceptions import MangoServerError, RESOURCE_ACCESS_DENIED


class TestSuiteDispositionService:
    @classmethod
    def update_diagnosis(cls, detail_id, failure_reason, failure_description, *, user, is_excluded=None):
        if not isinstance(failure_description, str) or not failure_description.strip():
            raise TestCenterError(TEST_REPORT_DISPOSITION_INVALID)
        values = {
            'failure_reason': failure_reason,
            'failure_description': failure_description,
        }
        if is_excluded is not None:
            values['is_excluded'] = is_excluded
        return cls.update(detail_id, values, user=user)

    @staticmethod
    def validate_id(detail_id):
        if not str(detail_id).isdigit() or isinstance(detail_id, bool):
            raise TestCenterError(TEST_REPORT_DISPOSITION_INVALID)
        return int(detail_id)

    @classmethod
    @transaction.atomic
    def update(cls, detail_id, values, *, user=None):
        detail_id = cls.validate_id(detail_id)
        suite_id = TestSuiteDetails.objects.filter(id=detail_id).values_list('test_suite_id', flat=True).first()
        suite = TestSuite.objects.select_for_update().filter(id=suite_id).first()
        if suite is None:
            raise TestCenterError(TEST_REPORT_NOT_FOUND)
        detail = TestSuiteDetails.objects.select_for_update().get(id=detail_id)
        if user is not None and not PermissionMenuService.is_effective_super_admin(user):
            if not ProjectProductScopeService.has_project_product(user, detail.project_product_id):
                raise MangoServerError(RESOURCE_ACCESS_DENIED)
        active = (TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value)
        if suite.status in active or TestSuiteDetails.objects.filter(test_suite_id=suite.id, status__in=active).exists():
            raise TestCenterError(TEST_REPORT_DISPOSITION_ACTIVE)
        allowed = {'is_excluded', 'failure_reason', 'failure_description'}
        if not values or set(values) - allowed:
            raise TestCenterError(TEST_REPORT_DISPOSITION_INVALID)
        if 'is_excluded' in values:
            if not isinstance(values['is_excluded'], bool):
                raise TestCenterError(TEST_REPORT_DISPOSITION_INVALID)
            if values['is_excluded'] and not (detail.status == TaskEnum.FAIL.value or detail.fail > 0):
                raise TestCenterError(TEST_REPORT_EXCLUSION_NOT_FAILED)
        if 'failure_reason' in values and values['failure_reason'] not in ('', *ReportFailureReasonEnum.obj()):
            raise TestCenterError(TEST_REPORT_DISPOSITION_INVALID)
        if 'failure_description' in values:
            text = values['failure_description']
            if not isinstance(text, str) or len(text) > 1000:
                raise TestCenterError(TEST_REPORT_DISPOSITION_INVALID)
            values['failure_description'] = text.strip()
        for key, value in values.items():
            setattr(detail, key, value)
        # 人工排查不能改执行耗时，保留原结果与执行时间。
        detail.save(update_fields=list(values))
        return {key: getattr(detail, key) for key in allowed}
