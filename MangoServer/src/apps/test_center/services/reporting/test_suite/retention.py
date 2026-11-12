from django.core.files.storage import default_storage
from django.db import transaction
from mangotools.enums import TaskEnum

from src.apps.task_center.enums.execution import ReportRetentionPolicyEnum
from src.apps.test_center.models import ExecutionResult, TestSuite, TestSuiteDetails
from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService
from src.common.logging import log


class TestSuiteRetentionService:
    """仅移除原始全成功报告的重数据，保留统计所需的轻量执行事实。"""

    @staticmethod
    def eligible(suite, rows):
        return (
            suite.report_retention_policy == ReportRetentionPolicyEnum.ABNORMAL_ONLY.value
            and suite.status == TaskEnum.SUCCESS.value
            and not suite.retained_summary
            and bool(rows)
            and all(row['status'] == TaskEnum.SUCCESS.value
                    and not row['fail'] and not row['warning'] and not row['is_excluded']
                    and not row['failure_reason'] and not row['failure_description']
                    and not row['error_message'] for row in rows)
        )

    @classmethod
    @transaction.atomic
    def cleanup(cls, suite_id):
        suite = TestSuite.objects.select_for_update().filter(id=suite_id).first()
        if suite is None or suite.retained_summary:
            return False
        details = TestSuiteDetails.objects.filter(test_suite_id=suite_id)
        rows = list(details.values('status', 'case_sum', 'success', 'fail', 'warning',
            'is_excluded', 'failure_reason', 'failure_description', 'error_message'))
        if not cls.eligible(suite, rows):
            return False
        snapshot = {
            'version': 1,
            'counter_data': TestSuiteSummaryService.counter_data(suite_id),
            'execution_summary': TestSuiteSummaryService.effective_summary_from_rows(rows),
        }
        if any(snapshot['counter_data'].get(key) for key in ('fail', 'warning', 'proceed', 'stay_begin', 'stopped', 'excluded_count')):
            return False
        # 文件删除失败时保留数据库明细，允许后续再次清理；不把异常报告误判为成功。
        for key in ExecutionResult.objects.filter(test_suite_id=suite_id).exclude(
                result_object_key__isnull=True).values_list('result_object_key', flat=True):
            if key:
                default_storage.delete(key)
        TestSuite.objects.filter(id=suite_id).update(retained_summary=snapshot, report_retained=False)
        details.delete()
        ExecutionResult.objects.filter(test_suite_id=suite_id).delete()
        return True

    @classmethod
    def cleanup_safely(cls, suite_id):
        try:
            return cls.cleanup(suite_id)
        except Exception:
            log.system.exception(f'成功报告清理失败，保留报告：test_suite={suite_id}')
            return False
