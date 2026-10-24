from mangotools.enums import StatusEnum

from src.apps.task_center.enums.execution import AutomationExecutionScopeEnum
from src.apps.task_center.exceptions import (
    TASK_SCHEDULE_CASE_REQUIRED,
    SYSTEM_TASK_CATEGORY_SCENARIO_TASK_EXECUTION_REQUIRED,
    SYSTEM_TASK_CATEGORY_TASK_EXECUTION_REQUIRED,
    SYSTEM_TASK_CATEGORY_MODULE_EXECUTION_REQUIRED,
    SYSTEM_TASK_CATEGORY_MODULE_EXECUTION_BINDING_NOT_ALLOWED,
    SYSTEM_TASK_CATEGORY_CASE_TASK_TYPE_BINDING_INVALID,
    SYSTEM_TASK_CATEGORY_PROJECT_PRODUCT_MODULE_INVALID,
    SYSTEM_TASK_CATEGORY_MINIMUM_REQUIRED,
    SYSTEM_TASK_CATEGORY_MODULE_TASK_EXECUTION_CREATE_NOT_ALLOWED,
    TaskCenterError,
)
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.task_center.services.selection.case_binding import TaskCaseBindingService
from src.apps.task_center.services.selection.case_selection import ScheduledTaskCaseSelectionService


class ScheduledTaskSaveValidationService:
    """集中处理普通定时任务创建、修改时的字段归一化和业务校验。"""

    @staticmethod
    def normalize_input(data):
        if 'api_concurrency_limit' not in data:
            return data
        normalized = data.copy()
        normalized['api_concurrency_limit'] = ApiConcurrencyService.validate_optional(
            data.get('api_concurrency_limit'),
            TaskCenterError,
        )
        return normalized

    @classmethod
    def validate(cls, attrs: dict, instance=None) -> dict:
        execution_scenes = ScheduledTaskCaseSelectionService.normalize_execution_scenes(
            attrs.get('execution_scenes', getattr(instance, 'execution_scenes', None)),
        )
        attrs['execution_scenes'] = execution_scenes
        execution_scope = attrs.get(
            'execution_scope',
            getattr(instance, 'execution_scope', AutomationExecutionScopeEnum.UNCLASSIFIED.value),
        )
        cls._validate_scope_change(instance, execution_scope)

        module = attrs.get('module', getattr(instance, 'module', None))
        case_types = ScheduledTaskCaseSelectionService.normalize_case_types(
            attrs.get('case_types', getattr(instance, 'case_types', [])),
        )
        attrs['case_types'] = case_types
        test_envs = ScheduledTaskCaseSelectionService.normalize_test_envs(
            attrs.get('test_envs', getattr(instance, 'test_envs', None)),
        )
        attrs['test_envs'] = test_envs

        timing_strategies = attrs.get('timing_strategies')
        if timing_strategies is None and instance is not None:
            timing_strategies = list(instance.timing_strategies.all())
        if not timing_strategies:
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_MINIMUM_REQUIRED)

        if (
                instance is not None
                and execution_scope == AutomationExecutionScopeEnum.MANUAL.value
                and case_types
                and instance.tasksdetails_set.exclude(type__in=case_types).exists()
        ):
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_CASE_TASK_TYPE_BINDING_INVALID)
        if not execution_scenes:
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_SCENARIO_TASK_EXECUTION_REQUIRED)
        if execution_scope == AutomationExecutionScopeEnum.UNCLASSIFIED.value:
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_TASK_EXECUTION_REQUIRED)
        if execution_scope == AutomationExecutionScopeEnum.MODULE.value and module is None:
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_MODULE_EXECUTION_REQUIRED)
        if execution_scope == AutomationExecutionScopeEnum.FULL_PRODUCT.value and module is not None:
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_MODULE_EXECUTION_BINDING_NOT_ALLOWED)

        ScheduledTaskCaseSelectionService.validate_environments_rule(
            execution_scenes=execution_scenes,
            execution_scope=execution_scope,
            test_envs=test_envs,
        )
        project_product = attrs.get(
            'project_product',
            getattr(instance, 'project_product', None),
        )
        if (
                module is not None
                and project_product is not None
                and module.project_product_id != project_product.id
        ):
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_PROJECT_PRODUCT_MODULE_INVALID)

        cls._validate_enabled_task(
            instance=instance,
            status=attrs.get('status', getattr(instance, 'status', None)),
            execution_scope=execution_scope,
            project_product=project_product,
            module=module,
            test_envs=test_envs,
            execution_scenes=execution_scenes,
            case_types=case_types,
        )
        return attrs

    @staticmethod
    def _validate_scope_change(instance, execution_scope: str) -> None:
        regular_scopes = {
            AutomationExecutionScopeEnum.MANUAL.value,
            AutomationExecutionScopeEnum.FULL_PRODUCT.value,
            AutomationExecutionScopeEnum.MODULE.value,
        }
        if instance is None and execution_scope not in regular_scopes:
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_MODULE_TASK_EXECUTION_CREATE_NOT_ALLOWED)
        if (
                instance is not None
                and execution_scope != instance.execution_scope
        ):
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_MODULE_TASK_EXECUTION_CREATE_NOT_ALLOWED)

    @staticmethod
    def _validate_enabled_task(
            *, instance, status, execution_scope, project_product, module,
            test_envs, execution_scenes, case_types,
    ) -> None:
        if status != StatusEnum.SUCCESS.value:
            return
        if execution_scope == AutomationExecutionScopeEnum.MANUAL.value:
            if instance is None:
                raise TaskCenterError(TASK_SCHEDULE_CASE_REQUIRED)
            for test_env in test_envs:
                details = TaskCaseBindingService.executable_details(instance, test_env=test_env)
                if case_types:
                    details = details.filter(type__in=case_types)
                if not details.exists():
                    raise TaskCenterError(TASK_SCHEDULE_CASE_REQUIRED)
            return

        for test_env in test_envs:
            selected = ScheduledTaskCaseSelectionService.select(
                project_product_id=project_product.id,
                module=module,
                test_env=test_env,
                execution_scenes=execution_scenes,
                execution_scope=execution_scope,
                case_types=case_types,
            )
            if not selected:
                raise TaskCenterError(TASK_SCHEDULE_CASE_REQUIRED)
