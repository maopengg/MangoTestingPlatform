from django.db import transaction
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.system.enums import TestSuiteNoticeEnum
from src.apps.task_center.enums.execution import AutomationExecutionSceneEnum, AutomationExecutionScopeEnum
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.common.utils.snowflake import Snowflake


class EvaluationReportService:
    """Store frozen evaluation summaries in the existing report lifecycle."""

    @staticmethod
    @transaction.atomic
    def create(*, product_id, module_id, test_env, user_id, case_id, name, count, payload):
        suite = TestSuite.objects.create(
            id=Snowflake.generate_id(), project_product_id=product_id, module_id=module_id,
            test_env=test_env, user_id=user_id, execution_name=name,
            execution_scenes=[AutomationExecutionSceneEnum.EFFECTIVENESS_TEST.value],
            execution_scope=AutomationExecutionScopeEnum.MANUAL.value,
            status=TaskEnum.STAY_BEGIN.value, is_notice=TestSuiteNoticeEnum.EXPIRED.value,
        )
        return TestSuiteDetails.objects.create(
            test_suite=suite, type=TestCaseTypeEnum.EVALUATION.value, project_product_id=product_id,
            test_env=test_env, case_id=case_id, case_name=name, case_sum=count,
            status=TaskEnum.STAY_BEGIN.value, retry=0,
            summary_data={"children": payload},
        ).id

    @staticmethod
    @transaction.atomic
    def update(detail_id, *, status, payload, count, success, fail, warning, error_message=None):
        detail = TestSuiteDetails.objects.select_related("test_suite").filter(
            pk=detail_id, type=TestCaseTypeEnum.EVALUATION.value,
        ).first()
        if detail is None:
            return
        suite = TestSuite.objects.select_for_update().get(pk=detail.test_suite_id)
        if not suite.report_retained:
            return
        TestSuiteDetails.objects.filter(pk=detail.id).update(
            status=status, case_sum=count, success=success, fail=fail, warning=warning,
            error_message=error_message, summary_data={"children": payload}, update_time=timezone.now(),
        )
        TestSuite.objects.filter(pk=suite.id).update(status=status, update_time=timezone.now())
