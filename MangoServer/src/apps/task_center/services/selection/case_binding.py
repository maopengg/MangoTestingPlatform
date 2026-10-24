from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Q

from src.apps.auto_api.models import ApiCase, ApiCaseRelease
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_pytest.models import PytestCase
from src.apps.auto_pytest.enums import PytestCasePublicationStatusEnum
from src.apps.auto_ui.models import UiCase
from src.apps.auto_ui.enums.case import UiCasePublicationStatusEnum
from src.apps.task_center.enums.execution import AutomationExecutionScopeEnum
from src.apps.task_center.exceptions import (
    SYSTEM_TASK_CATEGORY_CASE_EXECUTION_DELETE_NOT_ALLOWED,
    TaskCenterError,
)
from src.apps.task_center.models import Tasks, TasksDetails
from src.apps.task_center.services.selection.api_case_binding import ApiCaseTaskBindingService
from src.apps.task_center.services.selection.case_selection import ScheduledTaskCaseSelectionService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.services.product_module import ProductModuleService


@dataclass
class TaskCaseBindingResult:
    created_ids: list[int] = field(default_factory=list)
    updated_ids: list[int] = field(default_factory=list)
    removed_ids: list[int] = field(default_factory=list)
    skipped_ids: list[int] = field(default_factory=list)
    missing_ids: list[int] = field(default_factory=list)
    mismatched_ids: list[int] = field(default_factory=list)
    product_mismatched_ids: list[int] = field(default_factory=list)
    module_mismatched_ids: list[int] = field(default_factory=list)
    type_mismatched_ids: list[int] = field(default_factory=list)
    unpublished_ids: list[int] = field(default_factory=list)


class TaskCaseBindingService:
    CONFIG = {
        TestCaseTypeEnum.UI.value: (UiCase, "ui_case_id", "project_product_id", "module_id"),
        TestCaseTypeEnum.API.value: (ApiCase, "api_case_id", "project_product_id", "module_id"),
        TestCaseTypeEnum.PYTEST.value: (
            PytestCase,
            "pytest_case_id",
            "project_product__project_product_id",
            "module_id",
        ),
    }

    @classmethod
    def _config(cls, case_type: int):
        return cls.CONFIG[int(case_type)]

    @staticmethod
    def _normalize_ids(case_ids) -> list[int]:
        return list(dict.fromkeys(int(item) for item in (case_ids or [])))

    @classmethod
    def executable_details(cls, task: Tasks, *, test_env: int | None = None):
        effective_test_env = (
            ScheduledTaskCaseSelectionService.task_test_envs(task)[0]
            if test_env is None else test_env
        )
        execution_scenes = ScheduledTaskCaseSelectionService.task_execution_scenes(task)
        ScheduledTaskCaseSelectionService.validate_environment_rule(
            execution_scenes=execution_scenes,
            execution_scope=task.execution_scope,
            test_env=effective_test_env,
        )
        queryset = TasksDetails.objects.select_related(
            'ui_case',
            'api_case',
            'pytest_case',
        ).filter(task=task.id).filter(
            Q(type=TestCaseTypeEnum.API.value, api_case__isnull=False)
            | Q(
                type=TestCaseTypeEnum.UI.value,
                ui_case__isnull=False,
                ui_case__publication_status=UiCasePublicationStatusEnum.PUBLISHED.value,
            )
            | Q(
                type=TestCaseTypeEnum.PYTEST.value,
                pytest_case__isnull=False,
                pytest_case__publication_status=PytestCasePublicationStatusEnum.PUBLISHED.value,
            )
        )
        valid_detail_ids = []
        published_api_ids = set(ApiQuerySelector.current_published_case_releases().filter(
            api_case_id__in=queryset.filter(type=TestCaseTypeEnum.API.value).values('api_case_id'),
        ).values_list('api_case_id', flat=True))
        for detail in queryset:
            case = detail.ui_case or detail.api_case or detail.pytest_case
            if case is None:
                continue
            if detail.type == TestCaseTypeEnum.API.value and case.id not in published_api_ids:
                continue
            valid_detail_ids.append(detail.id)
        return queryset.filter(id__in=valid_detail_ids)

    @classmethod
    def inspect_bind(cls, task_id: int, case_type: int, case_ids) -> TaskCaseBindingResult:
        task = Tasks.objects.get(id=task_id)
        ids = cls._normalize_ids(case_ids)
        if task.execution_scope != AutomationExecutionScopeEnum.MANUAL.value:
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_CASE_EXECUTION_DELETE_NOT_ALLOWED)
        case_types = ScheduledTaskCaseSelectionService.normalize_case_types(task.case_types)
        if case_types and int(case_type) not in case_types:
            return TaskCaseBindingResult(
                type_mismatched_ids=ids,
                mismatched_ids=ids,
            )
        model, case_field, product_field, module_field = cls._config(case_type)
        rows = {
            case_id: (product_id, module_id)
            for case_id, product_id, module_id in model.objects.filter(id__in=ids).values_list(
                "id",
                product_field,
                module_field,
            )
        }
        if int(case_type) == TestCaseTypeEnum.PYTEST.value:
            unpublished_ids = list(model.objects.filter(id__in=ids).exclude(
                publication_status=PytestCasePublicationStatusEnum.PUBLISHED.value,
            ).values_list('id', flat=True))
        elif int(case_type) == TestCaseTypeEnum.UI.value:
            unpublished_ids = list(model.objects.filter(id__in=ids).exclude(
                publication_status=UiCasePublicationStatusEnum.PUBLISHED.value,
            ).values_list('id', flat=True))
        else:
            published_ids = set(ApiQuerySelector.current_published_case_releases().filter(
                api_case_id__in=ids,
            ).values_list('api_case_id', flat=True))
            unpublished_ids = [item for item in ids if item in rows and item not in published_ids]
        product_mismatched_ids = [
            item
            for item, (product_id, _) in rows.items()
            if task.project_product_id is not None and product_id != task.project_product_id
        ]
        allowed_module_ids = set(ProductModuleService.module_scope_ids(task.module_id)) if task.module_id else set()
        module_mismatched_ids = [
            item
            for item, (_, module_id) in rows.items()
            if item not in product_mismatched_ids
               and allowed_module_ids
               and module_id not in allowed_module_ids
        ]
        result = TaskCaseBindingResult(
            missing_ids=[item for item in ids if item not in rows],
            product_mismatched_ids=product_mismatched_ids,
            module_mismatched_ids=module_mismatched_ids,
            mismatched_ids=product_mismatched_ids + module_mismatched_ids,
            unpublished_ids=unpublished_ids,
        )
        eligible = set(rows) - set(result.mismatched_ids) - set(result.unpublished_ids)
        bound_ids = set(
            TasksDetails.objects.filter(
                task_id=task_id,
                type=case_type,
                **{f"{case_field}__in": eligible},
            ).values_list(case_field, flat=True)
        )
        result.updated_ids = [
            item for item in ids
            if case_type == TestCaseTypeEnum.API.value and item in bound_ids
        ]
        result.skipped_ids = [
            item for item in ids
            if case_type != TestCaseTypeEnum.API.value and item in bound_ids
        ]
        result.created_ids = [
            item for item in ids
            if item in eligible and item not in bound_ids
        ]
        return result

    @classmethod
    @transaction.atomic
    def bind(
            cls,
            task_id: int,
            case_type: int,
            case_ids,
            update_user_id: int | None = None,
    ) -> TaskCaseBindingResult:
        result = cls.inspect_bind(task_id, case_type, case_ids)
        if result.missing_ids or result.mismatched_ids or result.unpublished_ids:
            result.created_ids = []
            result.updated_ids = []
            return result
        valid_ids = result.created_ids + result.updated_ids
        _, case_field, _, _ = cls._config(case_type)
        created_ids = []
        updated_ids = []
        for case_id in valid_ids:
            if case_type == TestCaseTypeEnum.API.value:
                _, created = ApiCaseTaskBindingService.bind_current_published(
                    task_id=task_id,
                    case_id=case_id,
                    update_user_id=update_user_id,
                )
                (created_ids if created else updated_ids).append(case_id)
                continue
            _, created = TasksDetails.objects.get_or_create(
                task_id=task_id,
                type=case_type,
                **{case_field: case_id},
                defaults={"update_user_id": update_user_id},
            )
            (created_ids if created else result.skipped_ids).append(case_id)
        result.created_ids = created_ids
        result.updated_ids = updated_ids
        return result

    @classmethod
    def inspect_unbind(cls, task_id: int, case_type: int, case_ids) -> TaskCaseBindingResult:
        task = Tasks.objects.get(id=task_id)
        if task.execution_scope != AutomationExecutionScopeEnum.MANUAL.value:
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_CASE_EXECUTION_DELETE_NOT_ALLOWED)
        model, case_field, _, _ = cls._config(case_type)
        ids = cls._normalize_ids(case_ids)
        existing_ids = set(model.objects.filter(id__in=ids).values_list("id", flat=True))
        bound_ids = set(
            TasksDetails.objects.filter(
                task_id=task_id,
                type=case_type,
                **{f"{case_field}__in": existing_ids},
            ).values_list(case_field, flat=True)
        )
        return TaskCaseBindingResult(
            removed_ids=[item for item in ids if item in bound_ids],
            skipped_ids=[item for item in ids if item in existing_ids and item not in bound_ids],
            missing_ids=[item for item in ids if item not in existing_ids],
        )

    @classmethod
    @transaction.atomic
    def unbind(cls, task_id: int, case_type: int, case_ids) -> TaskCaseBindingResult:
        result = cls.inspect_unbind(task_id, case_type, case_ids)
        _, case_field, _, _ = cls._config(case_type)
        TasksDetails.objects.filter(
            task_id=task_id,
            type=case_type,
            **{f"{case_field}__in": result.removed_ids},
        ).delete()
        return result
