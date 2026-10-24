from collections.abc import Callable
from typing import TypeVar

from django.db import transaction

from src.apps.auto_api.models import ApiCase, ApiCaseDetailed, ApiCaseDetailedParameter

ResultType = TypeVar('ResultType')


class ApiCaseAggregateMutationService:
    """在同一事务内修改用例编辑态并刷新派生字段。"""

    @classmethod
    @transaction.atomic
    def mutate(
            cls,
            case_id: int,
            *,
            action: str,
            operation: Callable[[ApiCase], ResultType],
            operator_id: int | None = None,
            source: str = 'page',
            summary: str | None = None,
            refresh_case_flow: bool = True,
    ) -> ResultType:
        api_case = ApiCase.objects.select_for_update().get(id=case_id)
        result = operation(api_case)
        if refresh_case_flow:
            cls.rebuild_case_flow(case_id)
        return result

    @classmethod
    def rebuild_case_flow(cls, case_id: int) -> ApiCase:
        parameter_names = []
        steps = ApiCaseDetailed.objects.filter(case_id=case_id).select_related('api_info').order_by(
            'case_sort',
            'id',
        )
        for step in steps:
            names = list(
                ApiCaseDetailedParameter.objects.filter(
                    case_detailed_id=step.id,
                ).exclude(name='').exclude(name__isnull=True).order_by('id').values_list('name', flat=True)
            )
            parameter_names.extend(names or ([step.api_info.name] if step.api_info else []))
        api_case = ApiCase.objects.get(id=case_id)
        api_case.case_flow = cls.compose_case_flow(parameter_names)
        api_case.save(update_fields=['case_flow', 'update_time'])
        return api_case

    @staticmethod
    def compose_case_flow(parameter_names: list[str]) -> str | None:
        return f"->{'->'.join(parameter_names)}" if parameter_names else None
