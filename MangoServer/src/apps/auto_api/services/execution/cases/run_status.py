from collections import defaultdict
from datetime import datetime
from typing import Iterable

from django.db.models import Max, QuerySet
from django.utils import timezone
from mangotools.enums import StatusEnum
from mangotools.enums import TaskEnum

from src.apps.auto_api.models import ApiCase, ApiCaseDetailed, ApiCaseDetailedParameter
from src.apps.auto_api.schemas.execution import ApiCaseExecutionResult, ApiCaseStepResult


class ApiCaseRunStatusService:
    @classmethod
    def proceeding_case_candidates(cls, limit: int) -> list[tuple[int, datetime]]:
        candidates = {
            case_id: update_time
            for case_id, update_time in (
                ApiCase.objects.filter(status=TaskEnum.PROCEED.value)
                .order_by("id")
                .values_list("id", "update_time")[:limit]
            )
        }
        detailed_cases = ApiCaseDetailed.objects.filter(
            status=TaskEnum.PROCEED.value,
        ).values("case_id").annotate(
            latest_update_time=Max("update_time"),
        ).order_by("case_id").values_list(
            "case_id", "latest_update_time",
        )[:limit]
        for case_id, update_time in detailed_cases:
            current = candidates.get(case_id)
            if current is None or update_time > current:
                candidates[case_id] = update_time
        return list(candidates.items())[:limit]

    @classmethod
    def project_status(cls, case_id: int, status: int) -> int:
        """Project the latest execution status onto the case list snapshot."""
        now = timezone.now()
        updated = ApiCase.objects.filter(
            id=case_id,
            status=TaskEnum.PROCEED.value,
        ).update(status=status, update_time=now)
        updated += ApiCaseDetailed.objects.filter(
            case_id=case_id,
            status=TaskEnum.PROCEED.value,
        ).update(status=status, update_time=now)
        return updated

    @classmethod
    def scoped_steps(cls, case_id: int, case_sort: int | None) -> QuerySet:
        queryset = ApiCaseDetailed.objects.filter(case_id=case_id)
        if case_sort is not None and str(case_sort) != '':
            queryset = queryset.filter(case_sort__lte=case_sort)
        return queryset.order_by('case_sort')

    @classmethod
    def scoped_step_ids(cls, case_id: int, case_sort: int | None) -> list[int]:
        return list(cls.scoped_steps(case_id, case_sort).values_list('id', flat=True))

    @classmethod
    def reset_single_run(cls, case_id: int, case_sort: int | None):
        step_ids = cls.scoped_step_ids(case_id, case_sort)
        ApiCaseDetailed.objects.filter(id__in=step_ids).update(
            status=TaskEnum.STAY_BEGIN.value,
            error_message=None,
        )
        ApiCaseDetailedParameter.objects.filter(case_detailed_id__in=step_ids).update(
            status=TaskEnum.STAY_BEGIN.value,
        )

    @staticmethod
    def mark_step_running(step_id: int):
        ApiCaseDetailed.objects.filter(id=step_id).update(
            status=TaskEnum.PROCEED.value,
            error_message=None,
        )

    @staticmethod
    def mark_scenario_running(parameter_id: int):
        ApiCaseDetailedParameter.objects.filter(id=parameter_id).update(
            status=TaskEnum.PROCEED.value,
        )

    @staticmethod
    def finish_scenario(parameter_id: int, result_data: ApiCaseStepResult):
        ApiCaseDetailedParameter.objects.filter(id=parameter_id).update(
            status=result_data.status,
        )

    @staticmethod
    def finish_step(step_id: int, status: int, error_message: str | None = None):
        ApiCaseDetailed.objects.filter(id=step_id).update(
            status=status,
            error_message=error_message,
        )

    @staticmethod
    def finish_case(case_id: int, status: int):
        ApiCase.objects.filter(id=case_id).update(status=status)

    @classmethod
    def finalize_suite_run(cls, result: ApiCaseExecutionResult):
        steps = result.steps or []
        if not steps:
            cls.finish_case(result.id, result.status)
            return
        for step in steps:
            if step.parameter_id:
                cls.finish_scenario(step.parameter_id, step)
        for step_id, step_results in cls.group_steps(steps).items():
            status, error_message = cls.aggregate_step_status(step_results)
            cls.finish_step(step_id, status, error_message)
        cls.finish_case(result.id, result.status)

    @staticmethod
    def group_steps(steps: Iterable[ApiCaseStepResult]) -> dict[int, list[ApiCaseStepResult]]:
        grouped = defaultdict(list)
        for step in steps:
            grouped[step.id].append(step)
        return dict(grouped)

    @staticmethod
    def aggregate_step_status(steps: list[ApiCaseStepResult]) -> tuple[int, str | None]:
        latest_steps = ApiCaseRunStatusService.only_last_scenario_results(steps)
        for step in latest_steps:
            if step.status == StatusEnum.FAIL.value:
                return StatusEnum.FAIL.value, step.error_message
        for step in latest_steps:
            if step.status == TaskEnum.WARNING.value:
                return TaskEnum.WARNING.value, step.error_message
        return StatusEnum.SUCCESS.value, None

    @staticmethod
    def only_last_scenario_results(steps: list[ApiCaseStepResult]) -> list[ApiCaseStepResult]:
        result_map = {}
        order = []
        for step in steps:
            key = step.parameter_id if step.parameter_id is not None else f'{step.id}:{step.name}'
            if key not in result_map:
                order.append(key)
            result_map[key] = step
        return [result_map[key] for key in order]
