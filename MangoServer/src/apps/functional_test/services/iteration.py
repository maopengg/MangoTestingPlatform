# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import date

from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce

from src.apps.functional_test.enums import (
    FunctionalTestIterationStatusEnum,
    FunctionalRequirementTaskStatusEnum,
    ManualTestSuiteStatusEnum,
)
from src.apps.functional_test.exceptions import (
    FUNCTIONAL_TEST_ITERATION_NOT_ALLOWED,
    FUNCTIONAL_TEST_REQUIREMENT_ITERATION_NOT_ALLOWED,
    FUNCTIONAL_TEST_PLAN_NOT_ALLOWED,
    FUNCTIONAL_TEST_REQUIREMENT_ITERATION_INVALID,
    FUNCTIONAL_TEST_ITERATION_STATUS_REQUIRED,
    FUNCTIONAL_TEST_VERSION_PLAN_REQUIREMENT_ITERATION_DELETE_NOT_ALLOWED,
    FunctionalTestError,
)
from src.apps.functional_test.models import FunctionalTestDefect, FunctionalTestIteration, ManualTestSuite


class FunctionalTestIterationService:
    @staticmethod
    def validate_dates(start_date, end_date):
        if start_date and end_date and end_date < start_date:
            raise FunctionalTestError(FUNCTIONAL_TEST_ITERATION_NOT_ALLOWED)

    @classmethod
    def validate_schedule(
            cls,
            *,
            iteration: FunctionalTestIteration | None,
            development_owner_id: int | None,
            planned_start_date,
            planned_submit_date,
            status: int,
            allow_existing_iteration: bool = False,
    ):
        if bool(planned_start_date) != bool(planned_submit_date):
            raise FunctionalTestError(FUNCTIONAL_TEST_PLAN_NOT_ALLOWED)
        cls.validate_dates(planned_start_date, planned_submit_date)
        scheduled_statuses = {
            ManualTestSuiteStatusEnum.SCHEDULED.value,
            ManualTestSuiteStatusEnum.DEVELOPING.value,
            ManualTestSuiteStatusEnum.PENDING_TEST.value,
            ManualTestSuiteStatusEnum.TESTING.value,
            ManualTestSuiteStatusEnum.TEST_COMPLETED.value,
            ManualTestSuiteStatusEnum.PENDING_DEVELOPMENT.value,
            ManualTestSuiteStatusEnum.PENDING_RELEASE.value,
            ManualTestSuiteStatusEnum.RELEASED.value,
        }
        if status in scheduled_statuses and not (
                iteration and development_owner_id and planned_start_date and planned_submit_date
        ):
            raise FunctionalTestError(FUNCTIONAL_TEST_ITERATION_STATUS_REQUIRED)
        if not iteration:
            return
        if not allow_existing_iteration and iteration.status in (
                FunctionalTestIterationStatusEnum.COMPLETED.value,
                FunctionalTestIterationStatusEnum.CANCELLED.value,
        ):
            raise FunctionalTestError(FUNCTIONAL_TEST_REQUIREMENT_ITERATION_NOT_ALLOWED)
        if planned_start_date and (
                planned_start_date < iteration.start_date or planned_submit_date > iteration.end_date
        ):
            raise FunctionalTestError(FUNCTIONAL_TEST_REQUIREMENT_ITERATION_INVALID)

    @staticmethod
    def delete_iteration(iteration: FunctionalTestIteration):
        if iteration.requirement_versions.exists() or iteration.test_plans.exists():
            raise FunctionalTestError(FUNCTIONAL_TEST_VERSION_PLAN_REQUIREMENT_ITERATION_DELETE_NOT_ALLOWED)
        iteration.delete()

    @staticmethod
    def list_with_stats(queryset):
        open_defects = (
            FunctionalTestDefect.objects
            .exclude(status=4)
            .filter(
                Q(case_relations__plan_case__plan__iteration_id=OuterRef("pk"))
                | Q(requirement_version__iteration_ref_id=OuterRef("pk"))
                | Q(
                    case_relations__plan_case__plan__requirement_version__iteration_ref_id=OuterRef("pk"),
                )
                | Q(case_relations__case__suite__iteration_ref_id=OuterRef("pk"))
                | Q(
                    case_relations__case__requirement_bindings__requirement_version__iteration_ref_id=OuterRef("pk"),
                ),
            )
            .order_by()
            .annotate(group_key=Value(1))
            .values("group_key")
            .annotate(total=Count("id", distinct=True))
            .values("total")
        )
        return queryset.annotate(
            requirement_count=Count("requirement_versions", distinct=True),
            direct_plan_count=Count("test_plans", distinct=True),
            version_plan_count=Count("requirement_versions__test_plans", distinct=True),
            direct_case_count=Count("test_plans__plan_cases", distinct=True),
            version_case_count=Count("requirement_versions__test_plans__plan_cases", distinct=True),
            direct_executed_count=Count(
                "test_plans__plan_cases", filter=~Q(test_plans__plan_cases__result=0), distinct=True,
            ),
            version_executed_count=Count(
                "requirement_versions__test_plans__plan_cases",
                filter=~Q(requirement_versions__test_plans__plan_cases__result=0), distinct=True,
            ),
            direct_passed_count=Count(
                "test_plans__plan_cases", filter=Q(test_plans__plan_cases__result=1), distinct=True,
            ),
            version_passed_count=Count(
                "requirement_versions__test_plans__plan_cases",
                filter=Q(requirement_versions__test_plans__plan_cases__result=1), distinct=True,
            ),
            open_defect_count=Coalesce(
                Subquery(open_defects, output_field=IntegerField()), Value(0),
            ),
        )

    @staticmethod
    def _time_progress(start_date: date | None, end_date: date | None, today: date) -> float:
        if not start_date or not end_date:
            return 0
        if start_date == end_date:
            return 100 if today >= start_date else 0
        elapsed = (today - start_date).days
        duration = (end_date - start_date).days
        return round(max(0, min(100, elapsed / duration * 100)), 2)

    @classmethod
    def gantt(cls, iteration: FunctionalTestIteration, queryset=None) -> dict:
        today = date.today()
        rows = queryset if queryset is not None else ManualTestSuite.objects.all()
        rows = list(
            rows.filter(iteration_ref=iteration)
            .select_related("requirement", "development_owner", "owner", "module")
            .prefetch_related("requirement_tasks__owner")
            .order_by("development_owner__name", "planned_start_date", "id")
        )
        grouped = defaultdict(list)
        for suite in rows:
            tasks = list(suite.requirement_tasks.all())
            schedule_items = tasks or [None]
            for task in schedule_items:
                owner = task.owner if task else suite.development_owner
                start = task.planned_start_date if task else suite.planned_start_date
                end = task.planned_end_date if task else suite.planned_submit_date
                requirement_name = suite.requirement_name or (
                    suite.requirement.name if suite.requirement_id else "未命名需求"
                )
                grouped[owner.id if owner else 0].append({
                    "id": f"task-{task.id}" if task else f"requirement-{suite.id}",
                    "suite_id": suite.id,
                    "task_id": task.id if task else None,
                    "item_kind": "task" if task else "requirement",
                    "requirement_id": suite.requirement_id,
                    "requirement_key": suite.requirement.requirement_key if suite.requirement_id else "-",
                    "requirement_name": f"{requirement_name} · {task.name}" if task else requirement_name,
                    "version_no": suite.version_no,
                    "priority": suite.priority,
                    "status": suite.status,
                    "task_status": task.status if task else None,
                    "planned_start_date": start,
                    "planned_submit_date": end,
                    "actual_submit_at": task.actual_end_at if task else suite.actual_submit_at,
                    "time_progress": cls._time_progress(start, end, today),
                    "overdue": bool(
                        end and today > end and (
                                task is None or task.status != FunctionalRequirementTaskStatusEnum.COMPLETED.value
                        )
                    ),
                    "owner": owner,
                })

        groups = []
        for owner_id, items in grouped.items():
            for item in items:
                overlaps = [
                    other for other in items
                    if other["id"] != item["id"]
                       and item["planned_start_date"] and item["planned_submit_date"]
                       and other["planned_start_date"] and other["planned_submit_date"]
                       and item["planned_start_date"] <= other["planned_submit_date"]
                       and other["planned_start_date"] <= item["planned_submit_date"]
                ]
                item["overlap"] = bool(overlaps)
                item["overlap_with"] = [other["requirement_name"] for other in overlaps]
                item.pop("owner", None)
            owner = next(
                (task.owner for suite in rows for task in suite.requirement_tasks.all() if task.owner_id == owner_id),
                None)
            if owner is None:
                owner = next((suite.development_owner for suite in rows if suite.development_owner_id == owner_id),
                             None)
            groups.append({
                "owner_id": owner_id or None,
                "owner_name": owner.name if owner else "未分配",
                "items": items,
            })
        groups.sort(key=lambda item: (item["owner_id"] is None, item["owner_name"]))
        return {
            "iteration": {
                "id": iteration.id,
                "iteration_no": iteration.iteration_no,
                "name": iteration.name,
                "start_date": iteration.start_date,
                "end_date": iteration.end_date,
                "status": iteration.status,
            },
            "today": today,
            "groups": groups,
            "summary": {
                "owner_count": len([item for item in groups if item["owner_id"]]),
                "requirement_count": len(rows),
                "overdue_count": sum(bar["overdue"] for group in groups for bar in group["items"]),
                "overlap_count": sum(bar["overlap"] for group in groups for bar in group["items"]),
            },
        }
