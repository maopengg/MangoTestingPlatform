# -*- coding: utf-8 -*-
from copy import deepcopy

from django.db import transaction
from django.db.models import Count, Max, Prefetch
from django.utils import timezone

from src.apps.functional_test.enums import (
    FunctionalTestPlanStatusEnum,
    FunctionalTestResultEnum,
    ManualTestSuiteStatusEnum,
)
from src.apps.functional_test.exceptions import (
    FUNCTIONAL_TEST_PLAN_NOT_FOUND,
    FUNCTIONAL_TEST_PROJECT_PRODUCT_CASE_PLAN_INVALID,
    FUNCTIONAL_TEST_CASE_REQUIRED,
    FUNCTIONAL_TEST_PLAN_STATUS_EXECUTION_NOT_ALLOWED,
    FUNCTIONAL_TEST_CASE_PLAN_NOT_FOUND,
    FUNCTIONAL_TEST_STEP_RESULT_INVALID,
    FUNCTIONAL_TEST_RESULT_INVALID,
    FunctionalTestError,
)
from src.apps.functional_test.models import (
    FunctionalTestPlan, FunctionalTestPlanCase, ManualTestAutomationBinding, ManualTestCase,
)
from src.apps.functional_test.services.case_version import ManualTestCaseVersionService
from src.apps.functional_test.services.suite import ManualTestSuiteService


class FunctionalTestExecutionService:
    """单次测试计划的选例、执行和结果服务。"""

    CASE_SNAPSHOT_FIELDS = (
        "case_no", "title", "project_product_id", "module_id", "category_level_1",
        "category_level_2", "category_level_3", "priority", "test_types", "story_refs",
        "precondition", "test_point", "test_steps", "expected_result", "acceptance_source",
        "owner_id", "automation_status", "scenario_layer", "scenario_type", "scenario_tags",
        "test_data", "remark",
    )

    @classmethod
    def case_snapshot(cls, case: ManualTestCase) -> dict:
        snapshot = {field: deepcopy(getattr(case, field)) for field in cls.CASE_SNAPSHOT_FIELDS}
        snapshot["automation_bindings"] = ManualTestCaseVersionService.automation_bindings_snapshot(case)
        return snapshot

    @staticmethod
    def _require_plan(plan_id: int) -> FunctionalTestPlan:
        plan = FunctionalTestPlan.objects.select_for_update().filter(id=plan_id).first()
        if not plan:
            raise FunctionalTestError(FUNCTIONAL_TEST_PLAN_NOT_FOUND)
        return plan

    @staticmethod
    def _ensure_plan_editable(plan: FunctionalTestPlan):
        if plan.status in (FunctionalTestPlanStatusEnum.COMPLETED.value, FunctionalTestPlanStatusEnum.CLOSED.value):
            raise FunctionalTestError(FUNCTIONAL_TEST_PLAN_STATUS_EXECUTION_NOT_ALLOWED)

    @staticmethod
    def _ensure_plan_scope_editable(plan: FunctionalTestPlan):
        if plan.status not in (FunctionalTestPlanStatusEnum.DRAFT.value, FunctionalTestPlanStatusEnum.READY.value):
            raise FunctionalTestError(FUNCTIONAL_TEST_PLAN_STATUS_EXECUTION_NOT_ALLOWED)

    @classmethod
    @transaction.atomic
    def add_plan_cases(cls, plan_id: int, case_ids: list[int]) -> dict:
        plan = cls._require_plan(plan_id)
        cls._ensure_plan_scope_editable(plan)
        normalized_ids = list(dict.fromkeys(int(item) for item in case_ids if str(item).isdigit()))
        if not normalized_ids:
            raise FunctionalTestError(FUNCTIONAL_TEST_CASE_REQUIRED)
        bindings = ManualTestAutomationBinding.objects.select_related("api_case", "ui_case")
        cases = list(ManualTestCase.objects.filter(id__in=normalized_ids).prefetch_related(
            Prefetch("manualtestautomationbinding_set", queryset=bindings, to_attr="prefetched_bindings")
        ).order_by("id"))
        if not cases:
            raise FunctionalTestError(FUNCTIONAL_TEST_CASE_REQUIRED)
        if any(case.project_product_id != plan.project_product_id for case in cases):
            raise FunctionalTestError(FUNCTIONAL_TEST_PROJECT_PRODUCT_CASE_PLAN_INVALID)
        existing = set(FunctionalTestPlanCase.objects.filter(plan=plan, case_id__in=normalized_ids)
                       .values_list("case_id", flat=True))
        next_sort = FunctionalTestPlanCase.objects.filter(plan=plan).aggregate(value=Max("sort"))["value"] or 0
        created = []
        for case in cases:
            if case.id in existing:
                continue
            next_sort += 10
            created.append(FunctionalTestPlanCase(
                plan=plan, case=case, case_snapshot=cls.case_snapshot(case),
                library_case_version=case.version_no, sort=next_sort,
            ))
        FunctionalTestPlanCase.objects.bulk_create(created)
        return {"created_count": len(created), "ignored_count": len(existing)}

    @classmethod
    @transaction.atomic
    def copy_plan_cases(cls, plan_id: int, source_plan_id: int) -> dict:
        plan = cls._require_plan(plan_id)
        cls._ensure_plan_scope_editable(plan)
        source_plan = FunctionalTestPlan.objects.get(id=source_plan_id)
        if source_plan.project_product_id != plan.project_product_id:
            raise FunctionalTestError(FUNCTIONAL_TEST_PROJECT_PRODUCT_CASE_PLAN_INVALID)
        source_cases = list(FunctionalTestPlanCase.objects.filter(plan=source_plan).order_by("sort", "id"))
        if not source_cases:
            raise FunctionalTestError(FUNCTIONAL_TEST_CASE_REQUIRED)
        existing = set(FunctionalTestPlanCase.objects.filter(plan=plan).values_list("case_id", flat=True))
        next_sort = FunctionalTestPlanCase.objects.filter(plan=plan).aggregate(value=Max("sort"))["value"] or 0
        created = []
        for item in source_cases:
            if item.case_id in existing:
                continue
            next_sort += 10
            created.append(FunctionalTestPlanCase(
                plan=plan, case_id=item.case_id, case_snapshot=deepcopy(item.case_snapshot),
                library_case_version=item.library_case_version, sort=next_sort,
            ))
        FunctionalTestPlanCase.objects.bulk_create(created)
        copied_ids = {item.case_id for item in source_cases}
        return {"created_count": len(created), "ignored_count": len(existing.intersection(copied_ids))}

    @classmethod
    @transaction.atomic
    def remove_plan_cases(cls, plan_id: int, plan_case_ids: list[int]) -> int:
        plan = cls._require_plan(plan_id)
        cls._ensure_plan_scope_editable(plan)
        queryset = FunctionalTestPlanCase.objects.filter(plan=plan, id__in=plan_case_ids)
        count = queryset.count()
        queryset.delete()
        return count

    @classmethod
    @transaction.atomic
    def start_plan(
            cls,
            plan_id: int,
            user_id: int | None,
            *,
            update_requirement_status: bool = False,
    ) -> FunctionalTestPlan:
        plan = cls._require_plan(plan_id)
        cls._ensure_plan_editable(plan)
        if not FunctionalTestPlanCase.objects.filter(plan=plan).exists():
            raise FunctionalTestError(FUNCTIONAL_TEST_CASE_REQUIRED)
        if plan.status in (FunctionalTestPlanStatusEnum.DRAFT.value, FunctionalTestPlanStatusEnum.READY.value):
            plan.status = FunctionalTestPlanStatusEnum.RUNNING.value
            plan.started_at = plan.started_at or timezone.now()
            plan.update_user_id = user_id
            plan.save(update_fields=["status", "started_at", "update_user", "update_time"])
            if update_requirement_status and plan.requirement_version_id:
                plan.requirement_version.__class__.objects.filter(
                    id=plan.requirement_version_id,
                    status__in=[
                        ManualTestSuiteStatusEnum.SCHEDULED.value,
                        ManualTestSuiteStatusEnum.DEVELOPING.value,
                        ManualTestSuiteStatusEnum.PENDING_TEST.value,
                    ],
                ).update(status=ManualTestSuiteStatusEnum.TESTING.value, update_user_id=user_id)
        return plan

    @classmethod
    @transaction.atomic
    def finish_plan(cls, plan_id: int, user_id: int | None) -> FunctionalTestPlan:
        plan = cls._require_plan(plan_id)
        cls._ensure_plan_editable(plan)
        if plan.status != FunctionalTestPlanStatusEnum.RUNNING.value:
            raise FunctionalTestError(FUNCTIONAL_TEST_PLAN_STATUS_EXECUTION_NOT_ALLOWED)
        plan.status = FunctionalTestPlanStatusEnum.COMPLETED.value
        plan.finished_at = timezone.now()
        plan.update_user_id = user_id
        plan.save(update_fields=["status", "finished_at", "update_user", "update_time"])
        return plan

    @classmethod
    @transaction.atomic
    def update_plan_case(cls, plan_case_id: int, payload: dict, user_id: int | None) -> FunctionalTestPlanCase:
        item = FunctionalTestPlanCase.objects.select_for_update().select_related("plan").filter(id=plan_case_id).first()
        if not item:
            raise FunctionalTestError(FUNCTIONAL_TEST_CASE_PLAN_NOT_FOUND)
        cls._ensure_plan_editable(item.plan)
        if "test_steps" in payload:
            steps = payload.get("test_steps")
            if not isinstance(steps, list) or any(
                    not isinstance(step, dict) or not (step.get("action") or step.get("expected")) for step in steps
            ):
                raise FunctionalTestError(FUNCTIONAL_TEST_STEP_RESULT_INVALID)
        if "result" in payload and payload.get("result") not in FunctionalTestResultEnum.get_key_list():
            raise FunctionalTestError(FUNCTIONAL_TEST_RESULT_INVALID)
        snapshot = deepcopy(item.case_snapshot)
        for field in cls.CASE_SNAPSHOT_FIELDS:
            if field in payload:
                snapshot[field] = deepcopy(payload[field])
        if "project_product_id" in payload or "module_id" in payload:
            ManualTestSuiteService.validate_module_product(snapshot.get("project_product_id"),
                                                           snapshot.get("module_id"))
        item.case_snapshot = snapshot
        update_fields = ["case_snapshot", "update_time"]
        if "sort" in payload:
            item.sort = max(0, int(payload["sort"]))
            update_fields.append("sort")
        if "result" in payload:
            if item.plan.status != FunctionalTestPlanStatusEnum.RUNNING.value:
                raise FunctionalTestError(FUNCTIONAL_TEST_PLAN_STATUS_EXECUTION_NOT_ALLOWED)
            item.result = payload["result"]
            item.executor_id = user_id if item.result != FunctionalTestResultEnum.UNEXECUTED.value else None
            item.execute_time = timezone.now() if item.executor_id else None
            update_fields.extend(["result", "executor", "execute_time"])
        for field in ("actual_result", "execution_note"):
            if field in payload:
                setattr(item, field, payload.get(field))
                update_fields.append(field)
        item.save(update_fields=list(dict.fromkeys(update_fields)))
        return item

    @classmethod
    @transaction.atomic
    def batch_result(cls, plan_id: int, plan_case_ids: list[int], result: int, user_id: int | None):
        if result not in FunctionalTestResultEnum.get_key_list():
            raise FunctionalTestError(FUNCTIONAL_TEST_RESULT_INVALID)
        plan = cls._require_plan(plan_id)
        if plan.status != FunctionalTestPlanStatusEnum.RUNNING.value:
            raise FunctionalTestError(FUNCTIONAL_TEST_PLAN_STATUS_EXECUTION_NOT_ALLOWED)
        ids = [int(item) for item in plan_case_ids if str(item).isdigit()]
        now = timezone.now()
        FunctionalTestPlanCase.objects.filter(plan=plan, id__in=ids).update(
            result=result,
            executor_id=user_id if result != FunctionalTestResultEnum.UNEXECUTED.value else None,
            execute_time=now if result != FunctionalTestResultEnum.UNEXECUTED.value else None,
        )
        return list(FunctionalTestPlanCase.objects.filter(plan=plan, id__in=ids).select_related("case", "executor"))

    @staticmethod
    def plan_stats(plan_id: int) -> dict:
        rows = FunctionalTestPlanCase.objects.filter(plan_id=plan_id).values("result").annotate(count=Count("id"))
        counts = {result.value: 0 for result in FunctionalTestResultEnum}
        counts.update({item["result"]: item["count"] for item in rows})
        total = sum(counts.values())
        executed = total - counts[FunctionalTestResultEnum.UNEXECUTED.value]
        passed = counts[FunctionalTestResultEnum.PASSED.value]
        return {
            "total": total, "executed": executed,
            "progress": round(executed / total * 100, 2) if total else 0,
            "pass_rate": round(passed / executed * 100, 2) if executed else 0,
            "result_counts": counts,
        }
