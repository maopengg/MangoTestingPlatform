from django.utils import timezone

from src.apps.auto_api.selectors.execution_efficiency import ApiExecutionEfficiencySelector
from src.apps.data_factory.selectors.execution_progress import DatasourceExecutionProgressSelector


class DatasourceExecutionProgressService:
    @classmethod
    def for_attempts(cls, attempts, since):
        from src.apps.test_center.selectors.report_progress import ReportProgressSelector
        try:
            return cls.latest(ReportProgressSelector.running_owners(attempts=attempts), since)
        except Exception as error:
            return cls.unavailable(error)

    @staticmethod
    def unavailable(error):
        from src.common.logging import log
        log.system.warning('event=datasource_progress_evidence_unavailable exception_type=%s '
                           'action=retry_diagnostic_without_changing_case', type(error).__name__)
        return None

    @staticmethod
    def latest(owners, since):
        """只读诊断，关联精确执行项/代次；审计、步骤完成才是进展，续租不是。"""
        if not owners:
            return {}
        try:
            operations = DatasourceExecutionProgressSelector.latest_successful_operations(owners, since)
            steps = ApiExecutionEfficiencySelector.latest_step_activity(owners, since)
            result = {}
            for rows in (operations, steps):
                for detail_id, value in rows.items():
                    if timezone.is_naive(value):
                        value = timezone.make_aware(value, timezone.get_default_timezone())
                    result[detail_id] = max(result.get(detail_id, 0), value.timestamp())
            return result
        except Exception as error:
            return DatasourceExecutionProgressService.unavailable(error)
