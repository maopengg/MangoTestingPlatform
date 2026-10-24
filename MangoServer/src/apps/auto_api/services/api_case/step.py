from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from src.apps.auto_api.exceptions import (
    API_VERSION_API_INFO_REVISION_NOT_FOUND,
    API_VERSION_API_INFO_VERSION_INVALID,
    API_VERSION_CASE_SCENARIO_INVALID,
    API_VERSION_CASE_STEP_ORDER_INVALID,
    API_CASE_STEP_NOT_FOUND,
    AutoApiError,
)
from src.apps.auto_api.models import ApiCaseDetailed, ApiCaseDetailedParameter, ApiInfoRelease, ApiInfoRevision
from src.apps.auto_api.services.api_case.mutation import ApiCaseAggregateMutationService
from src.apps.auto_api.schemas.recovery import ApiStepExecutionConfig
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService


@dataclass(frozen=True)
class ApiCaseStepCreateResult:
    step: ApiCaseDetailed
    parameter: ApiCaseDetailedParameter
    api_info_revision_id: int | None


class ApiCaseStepService:
    """API Case 步骤与默认场景的通用创建/版本解析逻辑。"""

    @staticmethod
    def configure_recovery(step_id: int, config: dict, *, operator_id=None, source='page') -> dict:
        values = ApiStepExecutionConfig.parse_config(config).model_dump(exclude_defaults=True)
        step = ApiCaseDetailed.objects.filter(id=step_id).first()
        if step is None:
            raise AutoApiError(API_CASE_STEP_NOT_FOUND)

        def operation(_):
            step.execution_config = values
            step.update_user_id = operator_id
            step.save(update_fields=['execution_config', 'update_user', 'update_time'])
            return {'step_id': step.id, 'execution_config': values}

        return ApiCaseAggregateMutationService.mutate(
            step.case_id, action='configure_recovery', operation=operation,
            operator_id=operator_id, source=source,
        )

    @staticmethod
    def resolve_api_runtime(
            api_info_id: int,
            *,
            pinned_api_info_revision_id: int | None = None,
            allow_draft: bool = True,
    ):
        if pinned_api_info_revision_id:
            revision = ApiInfoRevision.objects.filter(
                id=pinned_api_info_revision_id,
                api_info_id=api_info_id,
            ).first()
            if revision is None:
                raise AutoApiError(API_VERSION_API_INFO_REVISION_NOT_FOUND)
            ApiInfoRevisionService.verify_revision(revision, executable=True)
            return ApiInfoRuntimeService.resolve_runtime(
                api_info_id,
                allow_draft=False,
                revision_id=revision.id,
            ), revision.id
        release = ApiInfoRelease.objects.filter(
            api_info_id=api_info_id,
            is_current=True,
            status=ApiInfoRelease.STATUS_PUBLISHED,
        ).select_related('revision').first()
        if release:
            ApiInfoRevisionService.verify_revision(release.revision, executable=True)
            revision = release.revision
            return ApiInfoRuntimeService.resolve_runtime(
                api_info_id,
                allow_draft=False,
                revision_id=revision.id,
            ), revision.id
        raise AutoApiError(API_VERSION_API_INFO_VERSION_INVALID)

    @classmethod
    def resolve_step_api_runtime(cls, step: ApiCaseDetailed, *, allow_draft: bool = True):
        return cls.resolve_api_runtime(
            step.api_info_id,
            pinned_api_info_revision_id=step.pinned_api_info_revision_id,
            allow_draft=allow_draft,
        )[0]

    @classmethod
    @transaction.atomic
    def create_step_with_default_parameter(
            cls,
            *,
            case_id: int,
            api_info_id: int,
            case_sort: int,
            operator_id: int | None = None,
            pinned_api_info_revision_id: int | None = None,
            execution_config: dict | None = None,
    ) -> ApiCaseStepCreateResult:
        config = ApiStepExecutionConfig.parse_config(
            {} if execution_config is None else execution_config,
        ).model_dump(exclude_defaults=True)
        api_info, resolved_revision_id = cls.resolve_api_runtime(
            api_info_id,
            pinned_api_info_revision_id=pinned_api_info_revision_id,
            allow_draft=True,
        )
        step = ApiCaseDetailed.objects.create(
            case_id=case_id,
            api_info_id=api_info_id,
            pinned_api_info_revision_id=resolved_revision_id,
            case_sort=case_sort,
            update_user_id=operator_id,
            execution_config=config,
        )
        parameter = ApiCaseDetailedParameter.objects.create(
            case_detailed=step,
            update_user_id=operator_id,
            name=api_info.name,
            headers=[],
            params=api_info.params,
            body_config=api_info.body_config,
            sse_config=api_info.sse_config,
        )
        return ApiCaseStepCreateResult(
            step=step,
            parameter=parameter,
            api_info_revision_id=resolved_revision_id,
        )

    @staticmethod
    def delete_step(
            step_id: int,
            *,
            operator_id: int | None = None,
            source: str = "page",
    ) -> dict:
        step = ApiCaseDetailed.objects.get(id=step_id)
        case_id = step.case_id
        parameter_count = ApiCaseDetailedParameter.objects.filter(
            case_detailed_id=step_id
        ).count()

        def operation(_):
            ApiCaseDetailed.objects.get(id=step_id).delete()

        ApiCaseAggregateMutationService.mutate(
            case_id,
            action="delete_step",
            operation=operation,
            operator_id=operator_id,
            source=source,
        )
        return {
            "case_id": case_id,
            "step_id": step_id,
            "deleted_parameter_count": parameter_count,
        }

    @staticmethod
    def delete_parameters(
            parameter_ids: list[int],
            *,
            operator_id: int | None = None,
            source: str = "page",
    ) -> dict:
        normalized_ids = list(dict.fromkeys(int(item) for item in parameter_ids))
        parameters = list(
            ApiCaseDetailedParameter.objects.select_related("case_detailed").filter(
                id__in=normalized_ids
            )
        )
        if len(parameters) != len(normalized_ids):
            raise ApiCaseDetailedParameter.DoesNotExist
        case_ids = {parameter.case_detailed.case_id for parameter in parameters}
        if len(case_ids) != 1:
            raise AutoApiError(API_VERSION_CASE_SCENARIO_INVALID)
        case_id = case_ids.pop()

        def operation(_):
            ApiCaseDetailedParameter.objects.filter(id__in=normalized_ids).delete()

        ApiCaseAggregateMutationService.mutate(
            case_id,
            action="delete_parameter",
            operation=operation,
            operator_id=operator_id,
            source=source,
        )
        return {
            "case_id": case_id,
            "deleted_parameter_ids": normalized_ids,
            "deleted_count": len(normalized_ids),
        }

    @staticmethod
    def sort_steps(
            case_id: int,
            sort_items: list[dict],
            *,
            operator_id: int | None = None,
            source: str = "page",
    ) -> list[dict]:
        normalized = [
            {
                "id": int(item.get("id") or item.get("step_id")),
                "case_sort": int(item["case_sort"]),
            }
            for item in sort_items
        ]
        if not normalized or not case_id:
            raise AutoApiError(API_VERSION_CASE_STEP_ORDER_INVALID)
        step_ids = [item["id"] for item in normalized]
        steps = list(ApiCaseDetailed.objects.filter(id__in=step_ids))
        if (
                len(steps) != len(set(step_ids))
                or {step.case_id for step in steps} != {int(case_id)}
        ):
            raise AutoApiError(API_VERSION_CASE_STEP_ORDER_INVALID)

        def operation(_):
            for item in normalized:
                step = ApiCaseDetailed.objects.select_for_update().get(
                    id=item["id"],
                    case_id=case_id,
                )
                step.case_sort = item["case_sort"]
                update_fields = ["case_sort", "update_time"]
                if operator_id is not None:
                    step.update_user_id = operator_id
                    update_fields.append("update_user")
                step.save(update_fields=update_fields)

        ApiCaseAggregateMutationService.mutate(
            case_id,
            action="sort_steps",
            operation=operation,
            operator_id=operator_id,
            source=source,
        )
        return normalized

    @classmethod
    def refresh_step_parameters(
            cls,
            step_id: int,
            *,
            operator_id: int | None = None,
            source: str = "page",
    ) -> int:
        step = ApiCaseDetailed.objects.select_related(
            "api_info",
            "pinned_api_info_revision",
        ).get(id=step_id)
        api_info = cls.resolve_step_api_runtime(step, allow_draft=True)
        updates = {
            "params": api_info.params,
            "body_config": api_info.body_config,
            "sse_config": api_info.sse_config,
            "update_time": timezone.now(),
        }
        if operator_id is not None:
            updates["update_user_id"] = operator_id

        return ApiCaseAggregateMutationService.mutate(
            step.case_id,
            action="refresh_api_info",
            operation=lambda _: ApiCaseDetailedParameter.objects.filter(
                case_detailed_id=step_id
            ).update(**updates),
            operator_id=operator_id,
            source=source,
            refresh_case_flow=False,
        )
