from copy import copy

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.auto_api.enums.module_coverage import (
    ModuleCoverageCaseStatus,
    ModuleCoverageExecutionResult,
)
from src.apps.auto_api.exceptions import (
    AutoApiError,
    MODULE_COVERAGE_ANALYSIS_BLOCKED,
)
from src.apps.auto_api.models import ApiCaseRevision
from src.apps.auto_api.models import (
    ModuleCoverageCase,
    ModuleCoverageCaseSnapshot,
)
from src.apps.test_center.models import ExecutionResult, ProjectProduct


class ModuleCoverageExecutionMixin:
    @classmethod
    def execution_result_from_status(cls, status: int | None) -> str | None:
        return {
            TaskEnum.SUCCESS.value: ModuleCoverageExecutionResult.PASSED,
            TaskEnum.FAIL.value: ModuleCoverageExecutionResult.FAILED,
            TaskEnum.WARNING.value: ModuleCoverageExecutionResult.PARTIAL,
        }.get(status)

    @classmethod
    def latest_api_case_execution(cls, api_case_id: int, *, revision_id=None) -> tuple[str | None, int | None]:
        rows = ExecutionResult.objects.filter(
            target_type="api_case",
            target_id=api_case_id,
            status__in=[TaskEnum.SUCCESS.value, TaskEnum.FAIL.value, TaskEnum.WARNING.value],
        )
        if revision_id is not None:
            rows = rows.filter(revision_id=revision_id)
        latest = rows.order_by("-create_time", "-id").only("status", "revision_id").first()
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
        rows = ModuleCoverageCase.objects.filter(
            api_case_id=api_case_id,
            status=ModuleCoverageCaseStatus.COMPLETED,
            removed_at__isnull=True,
        )
        pinned = ~Q(module_id=F('api_case__module_id'))
        same_module = rows.exclude(pinned).update(**updates)
        cross_module = rows.filter(pinned)
        # 跨模块复用固定修订，别的编辑态/修订执行不能给它补通过结果或换版本。
        if revision_id:
            same_module += cross_module.filter(api_case_revision_id=revision_id).update(execution_result=execution_result)
        return same_module

    @classmethod
    def repair_case_target(cls, item: ModuleCoverageCase):
        if not item.current_snapshot_id:
            return
        snapshot = item.current_snapshot
        if snapshot.interface_snapshot_id is None:
            cls.link_pending_case_snapshots(snapshot.scan, coverage_case_id=item.id)
        snapshot = ModuleCoverageCaseSnapshot.objects.select_related(
            "interface_snapshot__module_interface__current_snapshot__module_interface",
        ).get(id=snapshot.id)
        interface = snapshot.interface_snapshot
        if interface is None or interface.module_interface_id is None:
            return
        if (item.project_product_id, item.module_id, item.repository_key, item.branch,
                item.interface_source_key_hash, item.interface_source_key) != (
                interface.project_product_id, interface.module_id, interface.repository_key, interface.branch,
                interface.source_key_hash, interface.source_key):
            return
        if item.module_interface_id not in (None, interface.module_interface_id):
            return
        item.current_snapshot = snapshot
        item.module_interface = interface.module_interface
        assessment = cls.case_coverage_assessment(item, interface.module_interface.current_snapshot)
        item.coverage_validity = assessment["status"]
        item.coverage_validity_reason = assessment["reason"]
        item.save(update_fields=["module_interface", "coverage_validity", "coverage_validity_reason", "update_time"])

    @classmethod
    @transaction.atomic
    def backfill_missing_case_targets(cls, *, project_product_id=None, module_id=None) -> dict:
        from django.db.models import Q

        cases = ModuleCoverageCase.objects.filter(
            removed_at__isnull=True, current_snapshot__isnull=False,
        ).exclude(status=ModuleCoverageCaseStatus.REMOVED).filter(
            Q(module_interface__isnull=True) | Q(current_snapshot__interface_snapshot__isnull=True),
        )
        if project_product_id is not None:
            cases = cases.filter(project_product_id=project_product_id)
        if module_id is not None:
            cases = cases.filter(module_id=module_id)
        result = {"scanned": 0, "linked": 0, "unresolved": 0}
        for item in cases.select_related("current_snapshot__scan").order_by("project_product_id", "id").iterator(chunk_size=200):
            ProjectProduct.objects.select_for_update().get(id=item.project_product_id)
            item = ModuleCoverageCase.objects.select_for_update().get(id=item.id)
            cls.repair_case_target(item)
            result["scanned"] += 1
            complete = bool(item.module_interface_id and item.current_snapshot.interface_snapshot_id)
            result["linked" if complete else "unresolved"] += 1
        return result

    @classmethod
    @transaction.atomic
    def bind_api_case(cls, coverage_case_id: int, api_case_id: int, *,
                      api_case_revision_id: int | None = None) -> ModuleCoverageCase:
        item = ModuleCoverageCase.objects.get(id=coverage_case_id, removed_at__isnull=True)
        ProjectProduct.objects.select_for_update().get(id=item.project_product_id)
        item = ModuleCoverageCase.objects.select_for_update().get(id=coverage_case_id, removed_at__isnull=True)
        if item.api_case_id != api_case_id or (
                api_case_revision_id is not None and item.api_case_revision_id != api_case_revision_id):
            from src.apps.test_center.services.project.product_module import ProductModuleService
            ProductModuleService.validate_business_binding(item.module_id)
        cls.repair_case_target(item)
        if cls.interface_analysis_blocked(item):
            raise AutoApiError(MODULE_COVERAGE_ANALYSIS_BLOCKED)
        from src.apps.auto_api.services.coverage.parts.binding import ModuleCoverageCaseBindingService
        interface = item.current_snapshot.interface_snapshot if item.current_snapshot_id else None
        old_revision_id = item.api_case_revision_id if item.api_case_id == api_case_id else None
        revision_id = api_case_revision_id if api_case_revision_id is not None else old_revision_id
        api_case, preserved_revision = ModuleCoverageCaseBindingService.validate(
            item.project_product_id, item.module_id, api_case_id, revision_id,
            interface=interface, previous=item,
            coverage_payload=getattr(item.current_snapshot, 'payload', None) if item.current_snapshot_id else None)
        if api_case.module_id != item.module_id and (
                item.api_case_id != api_case_id or revision_id != old_revision_id):
            consumer = copy(item)
            consumer.api_case_id = None
            assessment = cls.case_coverage_assessment(consumer, interface)
            if assessment['status'] != 'valid':
                from src.apps.auto_api.exceptions import MODULE_COVERAGE_CASE_MODULE_MISMATCH
                raise AutoApiError(MODULE_COVERAGE_CASE_MODULE_MISMATCH,
                                  value=(item.module_id, api_case_id, api_case.module_id, assessment['reason']))
        item.api_case = api_case
        execution_result, executed_revision_id = cls.latest_api_case_execution(api_case.id,
            **({'revision_id': preserved_revision.id} if preserved_revision and (
                api_case.module_id != item.module_id or api_case_revision_id is not None) else {}))
        if api_case.module_id != item.module_id or api_case_revision_id is not None:
            item.api_case_revision = preserved_revision
        else:
            item.api_case_revision = (
                api_case.revisions.filter(id=executed_revision_id).first() if executed_revision_id else None
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
