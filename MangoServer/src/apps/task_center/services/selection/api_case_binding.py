from django.db import transaction
from django.utils import timezone

from src.apps.auto_api.exceptions import (
    API_VERSION_PROJECT_PRODUCT_CASE_TASK_BINDING_INVALID,
    API_VERSION_CASE_MODULE_TASK_BINDING_INVALID,
    AutoApiError,
)
from src.apps.auto_api.models import ApiCase
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.system.enums import TaskCaseVersionPolicyEnum, TaskCaseVersionStatusEnum
from src.apps.task_center.models import Tasks, TasksDetails
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.services.project.product_module import ProductModuleService


class ApiCaseTaskBindingService:
    """定时任务 API Case 固定绑定并执行当前已发布版本。"""

    VERSION_STATUS_PUBLISHED = TaskCaseVersionStatusEnum.PUBLISHED.value
    VERSION_STATUS_UNPUBLISHED = TaskCaseVersionStatusEnum.UNPUBLISHED.value

    @staticmethod
    def normalize_version_policy(value: str | None) -> str:
        return ApiCaseTaskBindingService.VERSION_STATUS_PUBLISHED

    @classmethod
    def resolve_execution_selection(cls, case_id: int, version_policy: str | None):
        return ApiCaseRevisionService.resolve_current_published(case_id)

    @classmethod
    def report_detail_version_policy(cls, detail) -> str:
        task_id = getattr(getattr(detail, 'test_suite', None), 'tasks_id', None)
        if task_id:
            version_policy = TasksDetails.objects.filter(
                task_id=task_id,
                type=TestCaseTypeEnum.API.value,
                api_case_id=detail.case_id,
            ).values_list('version_policy', flat=True).first()
            if version_policy:
                return cls.normalize_version_policy(version_policy)
        return cls.VERSION_STATUS_PUBLISHED

    @staticmethod
    def lock_and_validate_scope(task_id: int, case_id: int) -> None:
        task = Tasks.objects.select_for_update().get(id=task_id)
        case_scope = ApiCase.objects.filter(id=case_id).values(
            'project_product_id',
            'module_id',
        ).first()
        if case_scope is None:
            return
        if (
                task.project_product_id is not None
                and task.project_product_id != case_scope['project_product_id']
        ):
            raise AutoApiError(API_VERSION_PROJECT_PRODUCT_CASE_TASK_BINDING_INVALID)
        if (
                task.module_id is not None
                and case_scope['module_id'] not in ProductModuleService.module_scope_ids(task.module_id)
        ):
            raise AutoApiError(API_VERSION_CASE_MODULE_TASK_BINDING_INVALID)

    @classmethod
    @transaction.atomic
    def bind_current_published(
            cls,
            *,
            task_id: int,
            case_id: int,
            update_user_id: int | None,
    ) -> tuple[TasksDetails, bool]:
        return cls.bind_version_status(
            task_id=task_id,
            case_id=case_id,
            version_policy=cls.VERSION_STATUS_PUBLISHED,
            update_user_id=update_user_id,
        )

    @classmethod
    @transaction.atomic
    def bind_version_status(
            cls,
            *,
            task_id: int,
            case_id: int,
            version_policy: str | None,
            update_user_id: int | None,
    ) -> tuple[TasksDetails, bool]:
        cls.lock_and_validate_scope(task_id, case_id)
        detail = TasksDetails.objects.select_for_update().filter(
            task_id=task_id,
            type=TestCaseTypeEnum.API.value,
            api_case_id=case_id,
        ).first()
        normalized_policy = cls.normalize_version_policy(version_policy)
        selection = cls.resolve_execution_selection(case_id, normalized_policy)
        return cls._save_binding(
            detail=detail,
            task_id=task_id,
            case_id=case_id,
            selection=selection,
            update_user_id=update_user_id,
            version_policy=normalized_policy,
        )

    @classmethod
    @transaction.atomic
    def bind_release(
            cls,
            *,
            task_id: int,
            case_id: int,
            release_id: int,
            update_user_id: int | None,
    ) -> tuple[TasksDetails, bool]:
        """显式绑定历史或当前可执行 Release；已有绑定仅在该操作下升级。"""
        cls.lock_and_validate_scope(task_id, case_id)
        detail = TasksDetails.objects.select_for_update().filter(
            task_id=task_id,
            type=TestCaseTypeEnum.API.value,
            api_case_id=case_id,
        ).first()
        selection = ApiCaseRevisionService.resolve_release(case_id, release_id)
        return cls._save_binding(
            detail=detail,
            task_id=task_id,
            case_id=case_id,
            selection=selection,
            update_user_id=update_user_id,
            version_policy=TaskCaseVersionPolicyEnum.PINNED.value,
        )

    @staticmethod
    def _save_binding(
            *,
            detail: TasksDetails | None,
            task_id: int,
            case_id: int,
            selection,
            update_user_id: int | None,
            version_policy: str,
    ) -> tuple[TasksDetails, bool]:
        binding = {
            'type': TestCaseTypeEnum.API.value,
            'api_case_revision_id': selection.case_revision_id if selection else None,
            'api_case_release_id': selection.case_release_id if selection else None,
            'version_policy': version_policy,
            'bound_checksum': selection.checksum if selection else None,
            'update_user_id': update_user_id,
            'bound_at': timezone.now(),
        }
        if detail is None:
            return TasksDetails.objects.create(
                task_id=task_id,
                api_case_id=case_id,
                **binding,
            ), True

        for field, value in binding.items():
            setattr(detail, field, value)
        detail.save(update_fields=[*binding.keys()])
        return detail, False
