# -*- coding: utf-8 -*-
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from src.apps.functional_test.enums import FunctionalRequirementTaskStatusEnum
from src.apps.functional_test.exceptions import (
    FUNCTIONAL_TEST_TASK_PLAN_NOT_ALLOWED,
    FUNCTIONAL_TEST_PROJECT_PRODUCT_CASE_REQUIREMENT_REQUIRED,
    FunctionalTestError,
)
from src.apps.functional_test.models import (
    FunctionalRequirementCase,
    FunctionalRequirementTask,
    ManualTestCase,
    ManualTestSuite,
)
from src.apps.functional_test.services.suite import ManualTestSuiteService


class FunctionalRequirementService:
    @staticmethod
    def validate_task_dates(planned_start_date, planned_end_date):
        if planned_start_date and planned_end_date and planned_end_date < planned_start_date:
            raise FunctionalTestError(FUNCTIONAL_TEST_TASK_PLAN_NOT_ALLOWED)

    @classmethod
    def prepare_task_data(cls, payload: dict, instance: FunctionalRequirementTask | None = None) -> dict:
        data = dict(payload)
        start = data.get("planned_start_date", getattr(instance, "planned_start_date", None))
        end = data.get("planned_end_date", getattr(instance, "planned_end_date", None))
        cls.validate_task_dates(start, end)
        status = data.get("status", getattr(instance, "status", FunctionalRequirementTaskStatusEnum.PENDING.value))
        now = timezone.now()
        if status == FunctionalRequirementTaskStatusEnum.IN_PROGRESS.value and not getattr(instance, "actual_start_at",
                                                                                           None):
            data.setdefault("actual_start_at", now)
        if status == FunctionalRequirementTaskStatusEnum.COMPLETED.value:
            data.setdefault("actual_start_at", getattr(instance, "actual_start_at", None) or now)
            data.setdefault("actual_end_at", now)
        return data

    @staticmethod
    @transaction.atomic
    def bind_cases(requirement_version: ManualTestSuite, case_ids: list[int], user_id: int | None) -> int:
        normalized = list(dict.fromkeys(int(item) for item in case_ids if str(item).isdigit()))
        cases = list(ManualTestCase.objects.filter(id__in=normalized))
        if len(cases) != len(normalized) or any(
                item.project_product_id != requirement_version.project_product_id for item in cases
        ):
            raise FunctionalTestError(FUNCTIONAL_TEST_PROJECT_PRODUCT_CASE_REQUIREMENT_REQUIRED)
        existing = set(
            requirement_version.case_bindings.filter(case_id__in=normalized).values_list("case_id", flat=True)
        )
        max_sort = requirement_version.case_bindings.aggregate(value=Max("sort_order"))["value"] or 0
        bindings = []
        for offset, case in enumerate((item for item in cases if item.id not in existing), start=1):
            bindings.append(FunctionalRequirementCase(
                requirement_version=requirement_version,
                case=case,
                bound_case_version=case.version_no,
                sort_order=max_sort + offset,
                create_user_id=user_id,
            ))
        FunctionalRequirementCase.objects.bulk_create(bindings)
        ManualTestSuiteService.refresh_stats(requirement_version.id)
        return len(bindings)

    @staticmethod
    @transaction.atomic
    def unbind_cases(requirement_version: ManualTestSuite, case_ids: list[int]) -> int:
        normalized = list(dict.fromkeys(int(item) for item in case_ids if str(item).isdigit()))
        deleted, _ = requirement_version.case_bindings.filter(case_id__in=normalized).delete()
        legacy_count = ManualTestCase.objects.filter(
            id__in=normalized,
            suite=requirement_version,
        ).update(suite=None)
        ManualTestSuiteService.refresh_stats(requirement_version.id)
        return deleted + legacy_count
