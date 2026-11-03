from django.db import transaction
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.auto_api.enums.module_coverage import (
    ModuleCoverageCaseStatus,
    ModuleCoverageExecutionResult,
)
from src.apps.auto_api.exceptions import (
    AutoApiError,
    QUALITY_COVERAGE_PROJECT_PRODUCT_BINDING_NOT_FOUND,
    MODULE_COVERAGE_ANALYSIS_BLOCKED,
)
from src.apps.auto_api.models import ApiCase, ApiCaseRevision
from src.apps.auto_api.models import (
    ModuleCoverageCase,
)
from src.apps.test_center.models import ExecutionResult


class ModuleCoverageExecutionMixin:
    @classmethod
    def execution_result_from_status(cls, status: int | None) -> str | None:
        return {
            TaskEnum.SUCCESS.value: ModuleCoverageExecutionResult.PASSED,
            TaskEnum.FAIL.value: ModuleCoverageExecutionResult.FAILED,
            TaskEnum.WARNING.value: ModuleCoverageExecutionResult.PARTIAL,
        }.get(status)

    @classmethod
    def latest_api_case_execution(cls, api_case_id: int) -> tuple[str | None, int | None]:
        latest = ExecutionResult.objects.filter(
            target_type="api_case",
            target_id=api_case_id,
            status__in=[TaskEnum.SUCCESS.value, TaskEnum.FAIL.value, TaskEnum.WARNING.value],
        ).order_by("-create_time", "-id").only("status", "revision_id").first()
        if latest is None:
            return None, None
        return cls.execution_result_from_status(latest.status), latest.revision_id

    @classmethod
    def sync_api_case_execution_result(
            cls,
            api_case_id: int,
            status: int | None,
            revision_id: int | None = None,
    ) -> int:
        execution_result = cls.execution_result_from_status(status)
        if execution_result is None:
            return 0
        updates: dict = {"execution_result": execution_result}
        if revision_id and ApiCaseRevision.objects.filter(
                id=revision_id,
                api_case_id=api_case_id,
        ).exists():
            updates["api_case_revision_id"] = revision_id
        return ModuleCoverageCase.objects.filter(
            api_case_id=api_case_id,
            status=ModuleCoverageCaseStatus.COMPLETED,
            removed_at__isnull=True,
        ).update(**updates)

    @classmethod
    @transaction.atomic
    def bind_api_case(cls, coverage_case_id: int, api_case_id: int) -> ModuleCoverageCase:
        item = ModuleCoverageCase.objects.get(id=coverage_case_id, removed_at__isnull=True)
        if cls.interface_analysis_blocked(item):
            raise AutoApiError(MODULE_COVERAGE_ANALYSIS_BLOCKED)
        api_case = ApiCase.objects.filter(
            id=api_case_id,
            project_product_id=item.project_product_id,
            module_id=item.module_id,
        ).first()
        if api_case is None:
            raise AutoApiError(QUALITY_COVERAGE_PROJECT_PRODUCT_BINDING_NOT_FOUND)
        item.api_case = api_case
        execution_result, executed_revision_id = cls.latest_api_case_execution(api_case.id)
        item.api_case_revision = (
                                     api_case.revisions.filter(id=executed_revision_id).first()
                                     if executed_revision_id else None
                                 ) or api_case.revisions.order_by("-revision_no").first()
        item.status = ModuleCoverageCaseStatus.COMPLETED
        item.execution_result = execution_result or ModuleCoverageExecutionResult.NOT_EXECUTED
        item.save(update_fields=[
            "api_case", "api_case_revision", "status", "execution_result", "update_time",
        ])
        return item

    @staticmethod
    def archive_cases(ids: list[int]) -> int:
        return ModuleCoverageCase.objects.filter(id__in=ids, removed_at__isnull=True).update(
            status=ModuleCoverageCaseStatus.REMOVED,
            removed_at=timezone.now(),
        )
