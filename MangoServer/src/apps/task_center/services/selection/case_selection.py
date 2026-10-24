from dataclasses import dataclass

from django.db.models import QuerySet

from src.apps.auto_api.enums.case import ApiCaseScenarioTagEnum
from src.apps.auto_api.models import ApiCase, ApiCaseRelease
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_pytest.models import PytestCase
from src.apps.auto_pytest.enums import PytestCasePublicationStatusEnum
from src.apps.auto_ui.models import UiCase
from src.apps.auto_ui.enums.case import UiCasePublicationStatusEnum
from src.apps.task_center.enums.execution import (
    AutomationExecutionSceneEnum,
    AutomationExecutionScopeEnum,
)
from src.apps.task_center.exceptions import (
    SYSTEM_TASK_CATEGORY_MODULE_EXECUTION_REQUIRED,
    SYSTEM_TASK_CATEGORY_MODULE_EXECUTION_BINDING_NOT_ALLOWED,
    SYSTEM_TASK_CATEGORY_API_INFO_TYPE_REQUIRED,
    SYSTEM_TASK_CATEGORY_API_INFO_CASE_TYPE_REQUIRED,
    SYSTEM_TASK_CATEGORY_PROJECT_PRODUCT_MODULE_INVALID,
    SYSTEM_TASK_CATEGORY_SCENARIO_EXECUTION_INVALID,
    SYSTEM_TASK_CATEGORY_SCENARIO_EXECUTION_MINIMUM_REQUIRED,
    SYSTEM_TASK_CATEGORY_TEST_ENVIRONMENT_MINIMUM_REQUIRED,
    SYSTEM_TASK_CATEGORY_TEST_ENVIRONMENT_SCENARIO_EXECUTION_INVALID,
    SYSTEM_TASK_CATEGORY_TASK_INVALID,
    SYSTEM_TASK_CATEGORY_SCENARIO_TASK_EXECUTION_NOT_ALLOWED,
    TaskCenterError,
)
from src.apps.task_center.models import Tasks
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.services.product_module import ProductModuleService


@dataclass(frozen=True)
class ScheduledCaseItem:
    case_id: int
    case_name: str
    case_type: int
    project_product_id: int
    module_id: int | None
    module_full_path: str
    scenario_tags: list
    publication_status: str = "published"

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "case_name": self.case_name,
            "case_type": self.case_type,
            "project_product_id": self.project_product_id,
            "module_id": self.module_id,
            "module_full_path": self.module_full_path,
            "scenario_tags": self.scenario_tags,
            "publication_status": self.publication_status,
        }


class ScheduledTaskCaseSelectionService:
    SUPPORTED_CASE_TYPES = {
        TestCaseTypeEnum.UI.value,
        TestCaseTypeEnum.API.value,
        TestCaseTypeEnum.PYTEST.value,
    }
    PRODUCTION_SCENES = {
        AutomationExecutionSceneEnum.STABILITY_MONITORING.value,
        AutomationExecutionSceneEnum.PRODUCTION_INSPECTION.value,
        AutomationExecutionSceneEnum.PRODUCTION_REGRESSION.value,
    }
    DYNAMIC_EXCLUDED_TAGS = {
        ApiCaseScenarioTagEnum.EFFECTIVENESS_TEST.value,
        ApiCaseScenarioTagEnum.TEMPORARY_VALIDATION.value,
        ApiCaseScenarioTagEnum.PERFORMANCE_TEST.value,
    }
    TASK_EXCLUDED_SCENES = {
        AutomationExecutionSceneEnum.EFFECTIVENESS_TEST.value,
    }

    @classmethod
    def scheduled_execution_scene_options(cls) -> dict[str, str]:
        return {
            key: title
            for key, title in AutomationExecutionSceneEnum.obj().items()
            if key != AutomationExecutionSceneEnum.UNCLASSIFIED.value
               and key not in cls.TASK_EXCLUDED_SCENES
        }

    @classmethod
    def normalize_execution_scenes(cls, value) -> list[str]:
        if value in (None, "", AutomationExecutionSceneEnum.UNCLASSIFIED.value):
            return []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, (list, tuple, set)):
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_SCENARIO_EXECUTION_MINIMUM_REQUIRED)
        allowed = set(AutomationExecutionSceneEnum.get_key_list()) - {
            AutomationExecutionSceneEnum.UNCLASSIFIED.value,
        }
        normalized = []
        for item in value:
            item = str(item).strip()
            if item in cls.TASK_EXCLUDED_SCENES:
                raise TaskCenterError(SYSTEM_TASK_CATEGORY_SCENARIO_TASK_EXECUTION_NOT_ALLOWED)
            if item not in allowed:
                raise TaskCenterError(SYSTEM_TASK_CATEGORY_SCENARIO_EXECUTION_MINIMUM_REQUIRED)
            if item not in normalized:
                normalized.append(item)
        return normalized

    @classmethod
    def task_execution_scenes(cls, task: Tasks) -> list[str]:
        return cls.normalize_execution_scenes(getattr(task, "execution_scenes", None))

    @classmethod
    def normalize_test_envs(cls, value) -> list[int]:
        if value in (None, "") or not isinstance(value, (list, tuple, set)):
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_TEST_ENVIRONMENT_MINIMUM_REQUIRED)
        allowed = set(EnvironmentEnum.get_key_list())
        normalized = []
        for item in value:
            if isinstance(item, (bool, float)):
                raise TaskCenterError(SYSTEM_TASK_CATEGORY_TEST_ENVIRONMENT_MINIMUM_REQUIRED)
            try:
                item = int(item)
            except (TypeError, ValueError) as error:
                raise TaskCenterError(SYSTEM_TASK_CATEGORY_TEST_ENVIRONMENT_MINIMUM_REQUIRED,
                                      error=str(error)) from error
            if item not in allowed:
                raise TaskCenterError(SYSTEM_TASK_CATEGORY_TEST_ENVIRONMENT_MINIMUM_REQUIRED)
            if item not in normalized:
                normalized.append(item)
        if not normalized:
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_TEST_ENVIRONMENT_MINIMUM_REQUIRED)
        return sorted(normalized)

    @classmethod
    def task_test_envs(cls, task: Tasks) -> list[int]:
        return cls.normalize_test_envs(getattr(task, "test_envs", None))

    @classmethod
    def normalize_case_types(cls, value) -> list[int]:
        if value in (None, ""):
            return []
        if not isinstance(value, (list, tuple, set)):
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_API_INFO_CASE_TYPE_REQUIRED)
        normalized = []
        for item in value:
            if isinstance(item, bool):
                raise TaskCenterError(SYSTEM_TASK_CATEGORY_API_INFO_CASE_TYPE_REQUIRED)
            try:
                item = int(item)
            except (TypeError, ValueError) as error:
                raise TaskCenterError(SYSTEM_TASK_CATEGORY_API_INFO_CASE_TYPE_REQUIRED, error=str(error)) from error
            if item == TestCaseTypeEnum.OTHER.value:
                raise TaskCenterError(SYSTEM_TASK_CATEGORY_API_INFO_TYPE_REQUIRED)
            if item not in cls.SUPPORTED_CASE_TYPES:
                raise TaskCenterError(SYSTEM_TASK_CATEGORY_API_INFO_CASE_TYPE_REQUIRED)
            if item not in normalized:
                normalized.append(item)
        return sorted(normalized)

    @classmethod
    def execution_scenes_for_environment(cls, execution_scenes, test_env: int) -> list[str]:
        scenes = cls.normalize_execution_scenes(execution_scenes)
        is_production = int(test_env) == EnvironmentEnum.PRO.value
        if is_production:
            return [scene for scene in scenes if scene in cls.PRODUCTION_SCENES]
        return [
            scene for scene in scenes
            if scene != AutomationExecutionSceneEnum.STABILITY_MONITORING.value
        ]

    @classmethod
    def required_tags(cls, execution_scenes, test_env: int | None) -> list[str]:
        if test_env is None:
            return cls.normalize_execution_scenes(execution_scenes)
        return cls.execution_scenes_for_environment(execution_scenes, test_env)

    @classmethod
    def manual_required_tags(cls, execution_scenes, test_env: int) -> list[str]:
        # 手动指定的 Case 以用户维护的绑定清单为准，执行场景只用于任务分类。
        return []

    @staticmethod
    def _has_tags(case_tags, required_tags: list[str]) -> bool:
        values = set(case_tags or [])
        if values.intersection(ScheduledTaskCaseSelectionService.DYNAMIC_EXCLUDED_TAGS):
            return False
        return bool(values.intersection(required_tags))

    @staticmethod
    def _module_path(module) -> str:
        if module is None:
            return ""
        return module.get_full_path()

    @classmethod
    def validate_scope(cls, *, execution_scope: str, module) -> None:
        if execution_scope == AutomationExecutionScopeEnum.MODULE.value and module is None:
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_MODULE_EXECUTION_REQUIRED)
        if execution_scope == AutomationExecutionScopeEnum.FULL_PRODUCT.value and module is not None:
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_MODULE_EXECUTION_BINDING_NOT_ALLOWED)

    @classmethod
    def validate_environment_rule(
            cls,
            *,
            execution_scenes=None,
            execution_scope: str,
            test_env: int,
    ) -> None:
        scenes = cls.normalize_execution_scenes(execution_scenes)
        if not scenes:
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_SCENARIO_EXECUTION_MINIMUM_REQUIRED)
        if execution_scope == AutomationExecutionScopeEnum.MANUAL.value:
            if (
                    AutomationExecutionSceneEnum.STABILITY_MONITORING.value in scenes
                    and test_env != EnvironmentEnum.PRO.value
            ):
                raise TaskCenterError(SYSTEM_TASK_CATEGORY_TASK_INVALID)
            return
        if test_env == EnvironmentEnum.PRO.value and not set(scenes).issubset(cls.PRODUCTION_SCENES):
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_SCENARIO_EXECUTION_INVALID)
        if (
                test_env != EnvironmentEnum.PRO.value
                and AutomationExecutionSceneEnum.STABILITY_MONITORING.value in scenes
        ):
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_TASK_INVALID)

    @classmethod
    def validate_environments_rule(
            cls,
            *,
            execution_scenes=None,
            execution_scope: str,
            test_envs,
    ) -> None:
        scenes = cls.normalize_execution_scenes(execution_scenes)
        environments = cls.normalize_test_envs(test_envs)
        if execution_scope == AutomationExecutionScopeEnum.MANUAL.value:
            if (
                    AutomationExecutionSceneEnum.STABILITY_MONITORING.value in scenes
                    and any(environment != EnvironmentEnum.PRO.value for environment in environments)
            ):
                raise TaskCenterError(SYSTEM_TASK_CATEGORY_TASK_INVALID)
            return
        has_production_environment = EnvironmentEnum.PRO.value in environments
        has_non_production_environment = any(
            environment != EnvironmentEnum.PRO.value for environment in environments
        )
        production_scenes = set(scenes).intersection(cls.PRODUCTION_SCENES)
        non_production_scenes = set(scenes) - cls.PRODUCTION_SCENES
        non_production_compatible_scenes = set(scenes) - {
            AutomationExecutionSceneEnum.STABILITY_MONITORING.value,
        }
        if (
                (has_production_environment and not production_scenes)
                or (has_non_production_environment and not non_production_compatible_scenes)
                or (
                AutomationExecutionSceneEnum.STABILITY_MONITORING.value in scenes
                and not has_production_environment
        )
                or (non_production_scenes and not has_non_production_environment)
        ):
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_TEST_ENVIRONMENT_SCENARIO_EXECUTION_INVALID)

    @classmethod
    def _module_ids(cls, execution_scope: str, module_id: int | None) -> list[int]:
        if execution_scope != AutomationExecutionScopeEnum.MODULE.value:
            return []
        return ProductModuleService.module_scope_ids(module_id)

    @classmethod
    def _base_queryset(cls, queryset: QuerySet, module_ids: list[int]) -> QuerySet:
        if module_ids:
            queryset = queryset.filter(module_id__in=module_ids)
        return ProductModuleService.with_full_paths(queryset, "module")

    @classmethod
    def select_task(cls, task: Tasks, *, test_env: int | None = None) -> list[ScheduledCaseItem]:
        environments = [test_env] if test_env is not None else cls.task_test_envs(task)
        unique_items = {}
        for environment in environments:
            items = cls.select(
                project_product_id=task.project_product_id,
                module=task.module,
                test_env=environment,
                execution_scenes=cls.task_execution_scenes(task),
                execution_scope=task.execution_scope,
                case_types=task.case_types,
            )
            for item in items:
                unique_items[(item.case_type, item.case_id)] = item
        return sorted(unique_items.values(), key=lambda item: (item.case_type, item.case_id))

    @classmethod
    def matching_environments_for_api_case(
            cls,
            task: Tasks,
            api_case: ApiCase,
            *,
            is_published: bool,
    ) -> list[int]:
        """返回规则任务可匹配当前 API Case 的环境，与正向动态选例规则保持一致。"""
        if task.execution_scope not in {
            AutomationExecutionScopeEnum.FULL_PRODUCT.value,
            AutomationExecutionScopeEnum.MODULE.value,
        }:
            return []
        if task.project_product_id != api_case.project_product_id or not is_published:
            return []
        try:
            case_types = cls.normalize_case_types(task.case_types)
            if case_types and TestCaseTypeEnum.API.value not in case_types:
                return []
            module_ids = cls._module_ids(task.execution_scope, task.module_id)
            if module_ids and api_case.module_id not in module_ids:
                return []
            environments = cls.task_test_envs(task)
            execution_scenes = cls.task_execution_scenes(task)
        except TaskCenterError:
            return []
        return [
            environment
            for environment in environments
            if cls._has_tags(
                api_case.scenario_tags,
                cls.execution_scenes_for_environment(execution_scenes, environment),
            )
        ]

    @classmethod
    def select(
            cls,
            *,
            project_product_id: int,
            module,
            test_env: int,
            execution_scenes=None,
            execution_scope: str,
            case_types,
    ) -> list[ScheduledCaseItem]:
        cls.validate_scope(execution_scope=execution_scope, module=module)
        if module is not None and module.project_product_id != int(project_product_id):
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_PROJECT_PRODUCT_MODULE_INVALID)
        scenes_for_environment = cls.execution_scenes_for_environment(execution_scenes, test_env)
        if execution_scope != AutomationExecutionScopeEnum.MANUAL.value and not scenes_for_environment:
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_TEST_ENVIRONMENT_SCENARIO_EXECUTION_INVALID)
        normalized_types = cls.normalize_case_types(case_types)
        selected_types = normalized_types or sorted(cls.SUPPORTED_CASE_TYPES)
        module_ids = cls._module_ids(execution_scope, getattr(module, "id", None))
        required_tags = cls.required_tags(execution_scenes, test_env)
        result: list[ScheduledCaseItem] = []

        if TestCaseTypeEnum.UI.value in selected_types:
            queryset = cls._base_queryset(
                UiCase.objects.filter(project_product_id=project_product_id,
                                      publication_status=UiCasePublicationStatusEnum.PUBLISHED.value),
                module_ids,
            )
            for case in queryset:
                if cls._has_tags(case.scenario_tags, required_tags):
                    result.append(ScheduledCaseItem(
                        case_id=case.id,
                        case_name=case.name,
                        case_type=TestCaseTypeEnum.UI.value,
                        project_product_id=case.project_product_id,
                        module_id=case.module_id,
                        module_full_path=cls._module_path(case.module),
                        scenario_tags=case.scenario_tags or [],
                    ))

        if TestCaseTypeEnum.API.value in selected_types:
            queryset = cls._base_queryset(
                ApiCase.objects.filter(project_product_id=project_product_id),
                module_ids,
            )
            published_case_ids = set(ApiQuerySelector.current_published_case_releases().filter(
                api_case_id__in=queryset.values("id"),
            ).values_list("api_case_id", flat=True))
            for case in queryset:
                if case.id in published_case_ids and cls._has_tags(case.scenario_tags, required_tags):
                    result.append(ScheduledCaseItem(
                        case_id=case.id,
                        case_name=case.name,
                        case_type=TestCaseTypeEnum.API.value,
                        project_product_id=case.project_product_id,
                        module_id=case.module_id,
                        module_full_path=cls._module_path(case.module),
                        scenario_tags=case.scenario_tags or [],
                    ))

        if TestCaseTypeEnum.PYTEST.value in selected_types:
            queryset = cls._base_queryset(
                PytestCase.objects.filter(
                    project_product__project_product_id=project_product_id,
                    publication_status=PytestCasePublicationStatusEnum.PUBLISHED.value,
                ),
                module_ids,
            ).select_related("project_product")
            for case in queryset:
                if cls._has_tags(case.scenario_tags, required_tags):
                    result.append(ScheduledCaseItem(
                        case_id=case.id,
                        case_name=case.name,
                        case_type=TestCaseTypeEnum.PYTEST.value,
                        project_product_id=case.project_product.project_product_id,
                        module_id=case.module_id,
                        module_full_path=cls._module_path(case.module),
                        scenario_tags=case.scenario_tags or [],
                    ))

        return sorted(result, key=lambda item: (item.case_type, item.case_id))

    @classmethod
    def summary(
            cls,
            items: list[ScheduledCaseItem],
            *,
            execution_scenes=None,
            test_env: int | None = None,
    ) -> dict:
        counts_by_case_type = {str(value): 0 for value in sorted(cls.SUPPORTED_CASE_TYPES)}
        counts_by_module: dict[int | None, dict] = {}
        for item in items:
            counts_by_case_type[str(item.case_type)] += 1
            module = counts_by_module.setdefault(item.module_id, {
                "module_id": item.module_id,
                "module_name": item.module_full_path,
                "count": 0,
            })
            module["count"] += 1
        return {
            "selected_count": len(items),
            "counts_by_case_type": counts_by_case_type,
            "counts_by_module": list(counts_by_module.values()),
            "excluded_counts": {},
            "required_tags": cls.required_tags(execution_scenes, test_env),
        }
