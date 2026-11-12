from dataclasses import dataclass
from typing import Any

from django.db import transaction

from src.apps.auto_api.schemas.case_schema import validate_scenario_tag_list
from src.apps.functional_test.enums import (
    FunctionalTestContextKeyEnum,
    FunctionalTestContextUrlTypeEnum,
    FunctionalTestPlanScopeTypeEnum,
    ManualTestCaseVersionSourceEnum,
)
from src.apps.functional_test.exceptions import (
    FUNCTIONAL_TEST_TYPE_SAVE_INVALID,
    FUNCTIONAL_TEST_CASE_PLAN_EXECUTION_DELETE_NOT_ALLOWED,
    FUNCTIONAL_TEST_VERSION_PLAN_REQUIREMENT_DELETE_NOT_ALLOWED,
    FUNCTIONAL_TEST_VERSION_PLAN_REQUIREMENT_TYPE_REQUIRED,
    FUNCTIONAL_TEST_PLAN_ITERATION_TYPE_REQUIRED,
    FUNCTIONAL_TEST_PROJECT_PRODUCT_CASE_PLAN_INVALID,
    FUNCTIONAL_TEST_STEP_RESULT_INVALID,
    FUNCTIONAL_TEST_DYNAMIC_ERROR,
    FUNCTIONAL_TEST_SUITE_REQUIRED,
    FUNCTIONAL_TEST_VERSION_REQUIREMENT_ITERATION_BINDING_INVALID,
    FUNCTIONAL_TEST_DATABASE_CASE_NOT_ALLOWED,
    FunctionalTestError,
)
from src.apps.functional_test.models import (
    FunctionalTestContextResource,
    FunctionalTestPlan,
    ManualTestCase,
    ManualTestSuite,
)
from src.apps.functional_test.services.cases.case_version import ManualTestCaseVersionService
from src.apps.functional_test.services.suites.suite import ManualTestSuiteService
from src.apps.test_center.services.project.product_module import ProductModuleService
from src.common.database import ModelMutationValidationError, save_model, validate_model


@dataclass
class FunctionalTestMutationResult:
    instance: Any = None
    errors: dict | None = None
    data: dict | None = None
    forbidden: bool = False


class FunctionalTestMutationService:
    BULK_EDITABLE_CASE_FIELDS = frozenset({
        "case_no",
        "title",
        "category_level_1",
        "category_level_2",
        "category_level_3",
        "priority",
        "test_types",
        "precondition",
        "test_point",
        "expected_result",
        "acceptance_source",
        "test_data",
        "owner_id",
        "project_product_id",
        "module_id",
        "scenario_layer",
        "scenario_type",
        "scenario_tags",
        "automation_status",
        "remark",
        "status",
    })

    @staticmethod
    def _save_model(model, data: dict, instance=None) -> FunctionalTestMutationResult:
        try:
            saved = save_model(model, data, instance=instance, partial=instance is not None)
        except ModelMutationValidationError as error:
            return FunctionalTestMutationResult(errors=error.errors)
        return FunctionalTestMutationResult(instance=saved)

    @staticmethod
    def _related(model, field_name: str, data: dict, instance=None):
        if field_name in data:
            value = data[field_name]
            if value is None or hasattr(value, "pk"):
                return value
            related_model = model._meta.get_field(field_name).related_model
            return related_model.objects.filter(id=value).first()
        return getattr(instance, field_name, None) if instance else None

    @classmethod
    def _validate_plan(cls, data: dict, instance=None) -> dict:
        attrs = dict(data)
        project_product = cls._related(FunctionalTestPlan, "project_product", attrs, instance)
        requirement_version = cls._related(FunctionalTestPlan, "requirement_version", attrs, instance)
        iteration = cls._related(FunctionalTestPlan, "iteration", attrs, instance)
        scope_type = attrs.get("scope_type", getattr(instance, "scope_type", None))
        if scope_type == FunctionalTestPlanScopeTypeEnum.REQUIREMENT.value and not requirement_version:
            raise FunctionalTestError(FUNCTIONAL_TEST_VERSION_PLAN_REQUIREMENT_TYPE_REQUIRED)
        if scope_type == FunctionalTestPlanScopeTypeEnum.SPRINT.value and not iteration:
            raise FunctionalTestError(FUNCTIONAL_TEST_PLAN_ITERATION_TYPE_REQUIRED)
        if scope_type == FunctionalTestPlanScopeTypeEnum.REQUIREMENT.value:
            attrs["requirement"] = requirement_version.requirement_id
            attrs["iteration"] = None
        else:
            attrs["requirement"] = None
            attrs["requirement_version"] = None
        if scope_type != FunctionalTestPlanScopeTypeEnum.SPRINT.value:
            attrs["iteration"] = None
            iteration = None
        if requirement_version and project_product and requirement_version.project_product_id != project_product.id:
            raise FunctionalTestError(FUNCTIONAL_TEST_PROJECT_PRODUCT_CASE_PLAN_INVALID)
        if iteration and project_product and iteration.project_product_id != project_product.id:
            raise FunctionalTestError(FUNCTIONAL_TEST_PROJECT_PRODUCT_CASE_PLAN_INVALID)
        return attrs

    @classmethod
    def _validate_suite(cls, data: dict, instance=None) -> dict:
        attrs = dict(data)
        if not (attrs.get("owner") or getattr(instance, "owner_id", None)):
            raise FunctionalTestError(FUNCTIONAL_TEST_SUITE_REQUIRED)
        if not (attrs.get("iteration_ref") or getattr(instance, "iteration_ref_id", None)):
            raise FunctionalTestError(FUNCTIONAL_TEST_VERSION_REQUIREMENT_ITERATION_BINDING_INVALID)
        ProductModuleService.validate_crud_binding(ManualTestSuite, attrs, instance)
        return attrs

    @classmethod
    def _validate_case(cls, data: dict, instance=None) -> dict:
        attrs = dict(data)
        for field in ("category_level_1", "category_level_2", "category_level_3"):
            if field in attrs and isinstance(attrs[field], str):
                attrs[field] = attrs[field].strip()
        if "scenario_tags" in attrs:
            attrs["scenario_tags"] = validate_scenario_tag_list(attrs["scenario_tags"])
        merged = {
            field: getattr(instance, f"{field}_id", None) if field in {"owner", "project_product",
                                                                       "module"} else getattr(instance, field, None)
            for field in (
                "case_no", "title", "category_level_1", "test_point", "test_steps",
                "test_types", "priority", "scenario_layer", "scenario_type",
                "scenario_tags", "owner", "project_product", "module",
            )
        } if instance else {}
        merged.update(attrs)
        errors = []
        for field, message in {"case_no": "用例编号不能为空", "title": "用例标题不能为空",
                               "test_point": "测试场景不能为空"}.items():
            if not str(merged.get(field) or "").strip():
                errors.append(message)
        steps = merged.get("test_steps") or []
        if not isinstance(steps, list) or any(
                not isinstance(step, dict) or not (
                        str(step.get("action") or "").strip() or str(step.get("expected") or "").strip())
                for step in steps
        ):
            raise FunctionalTestError(FUNCTIONAL_TEST_STEP_RESULT_INVALID)
        if not merged.get("test_types"):
            errors.append("测试类型不能为空")
        for field, message in {"priority": "优先级不能为空", "scenario_layer": "测试层级不能为空",
                               "scenario_type": "验证类型不能为空"}.items():
            if merged.get(field) in (None, ""):
                errors.append(message)
        if not merged.get("scenario_tags"):
            errors.append("执行场景不能为空")
        for field, message in {"owner": "负责人不能为空", "project_product": "项目产品不能为空",
                               "module": "模块不能为空"}.items():
            if not merged.get(field):
                errors.append(message)
        if errors:
            raise FunctionalTestError(FUNCTIONAL_TEST_DYNAMIC_ERROR, value=("；".join(errors),))
        ManualTestSuiteService.validate_module_product(merged["project_product"], merged["module"])
        return attrs

    @classmethod
    @transaction.atomic
    def create_plan(
            cls,
            payload: dict,
            user_id: int | None,
    ) -> FunctionalTestMutationResult:
        data = dict(payload)
        if user_id is not None:
            data["update_user"] = user_id
        return cls._save_model(FunctionalTestPlan, cls._validate_plan(data))

    @classmethod
    @transaction.atomic
    def create_suite(
            cls,
            payload: dict,
            user_id: int | None,
            data_validator=None,
    ) -> FunctionalTestMutationResult:
        data = ManualTestSuiteService.prepare_suite_data(payload, user_id)
        if user_id is not None:
            data["update_user"] = user_id
        if data_validator and not data_validator(data):
            transaction.set_rollback(True)
            return FunctionalTestMutationResult(forbidden=True)
        result = cls._save_model(ManualTestSuite, cls._validate_suite(data))
        if result.instance:
            ManualTestSuiteService.refresh_stats(result.instance.id)
        return result

    @classmethod
    @transaction.atomic
    def update_suite(
            cls,
            suite_id: int,
            payload: dict,
            user_id: int | None,
            data_validator=None,
    ) -> FunctionalTestMutationResult:
        suite = ManualTestSuite.objects.get(id=suite_id)
        data = ManualTestSuiteService.prepare_suite_data(payload, user_id, instance=suite)
        if user_id is not None:
            data["update_user"] = user_id
        if data_validator and not data_validator(data):
            transaction.set_rollback(True)
            return FunctionalTestMutationResult(forbidden=True)
        return cls._save_model(ManualTestSuite, cls._validate_suite(data, suite), suite)

    @staticmethod
    @transaction.atomic
    def delete_suites(suite_ids: list[int]) -> dict:
        suites = ManualTestSuite.objects.filter(id__in=suite_ids)
        if suites.filter(test_plans__isnull=False).exists():
            raise FunctionalTestError(FUNCTIONAL_TEST_VERSION_PLAN_REQUIREMENT_DELETE_NOT_ALLOWED)
        deleted_ids = list(suites.values_list("id", flat=True))
        retained_case_count = ManualTestCase.objects.filter(suite_id__in=deleted_ids).count()
        resource_count = FunctionalTestContextResource.objects.filter(
            suite_id__in=deleted_ids
        ).count()
        suites.delete()
        return {
            "deleted_suite_ids": deleted_ids,
            "deleted_count": len(deleted_ids),
            "retained_case_count": retained_case_count,
            "deleted_resource_count": resource_count,
        }

    @classmethod
    @transaction.atomic
    def create_case(
            cls,
            payload: dict,
            user_id: int | None,
            data_validator=None,
    ) -> FunctionalTestMutationResult:
        data = dict(payload)
        suite = ManualTestSuite.objects.filter(id=data.get("suite")).first()
        if suite:
            data.setdefault("owner", suite.owner_id)
            data["project_product"] = data.get("project_product") or suite.project_product_id
            data["module"] = data.get("module") or suite.module_id
        if user_id is not None:
            data["update_user"] = user_id
        if data_validator and not data_validator(data):
            return FunctionalTestMutationResult(forbidden=True)
        result = cls._save_model(ManualTestCase, cls._validate_case(data))
        if result.instance:
            ManualTestCaseVersionService.record(
                result.instance,
                source=ManualTestCaseVersionSourceEnum.LIBRARY.value,
                changed_by_id=user_id,
            )
            if result.instance.suite_id:
                ManualTestSuiteService.refresh_stats(result.instance.suite_id)
        return result

    @classmethod
    @transaction.atomic
    def bulk_create_cases(
            cls,
            items,
            user_id: int | None,
            data_validator=None,
    ) -> FunctionalTestMutationResult:
        if not isinstance(items, list) or not items or len(items) > 500:
            return FunctionalTestMutationResult(
                errors={"items": "批量创建必须包含 1-500 条用例"}
            )

        prepared = []
        validation_errors = {}
        for index, item in enumerate(items):
            row_number = index + 1
            if not isinstance(item, dict):
                validation_errors[str(row_number)] = {"row": "用例数据必须是对象"}
                continue
            data = dict(item)
            data.pop("draft_id", None)
            if "owner_id" in data:
                data["owner"] = data.pop("owner_id")
            if "project_product_id" in data:
                data["project_product"] = data.pop("project_product_id")
            if "module_id" in data:
                data["module"] = data.pop("module_id")
            if user_id is not None:
                data["update_user"] = user_id
            if data_validator and not data_validator(data):
                validation_errors[str(row_number)] = {"project_product": "暂无该项目产品的数据权限"}
                continue
            try:
                data = cls._validate_case(data)
            except FunctionalTestError as error:
                validation_errors[str(row_number)] = {"row": error.msg}
                continue
            prepared.append((row_number, data))

        if validation_errors:
            return FunctionalTestMutationResult(errors=validation_errors)

        created = []
        for row_number, data in prepared:
            result = cls._save_model(ManualTestCase, data)
            if result.errors:
                validation_errors[str(row_number)] = result.errors
                continue
            case = result.instance
            ManualTestCaseVersionService.record(
                case,
                source=ManualTestCaseVersionSourceEnum.LIBRARY.value,
                changed_by_id=user_id,
            )
            created.append(case)
        if validation_errors:
            transaction.set_rollback(True)
            return FunctionalTestMutationResult(errors=validation_errors)
        return FunctionalTestMutationResult(instance=created)

    @classmethod
    @transaction.atomic
    def update_case(
            cls,
            case_id: int,
            payload: dict,
            user_id: int | None,
    ) -> FunctionalTestMutationResult:
        case = ManualTestCase.objects.select_for_update().get(id=case_id)
        data = dict(payload)
        expected_version = data.pop("expected_version", data.get("version_no"))
        if expected_version not in (None, ""):
            try:
                expected_version = int(expected_version)
            except (TypeError, ValueError):
                return FunctionalTestMutationResult(errors={"version_no": "版本号必须是整数"})
            if expected_version != case.version_no:
                return FunctionalTestMutationResult(data={
                    "conflicts": [{
                        "id": case.id,
                        "expected_version": expected_version,
                        "current_version": case.version_no,
                    }]
                })
        previous_suite_id = case.suite_id
        ManualTestCaseVersionService.ensure_baseline(case)
        data["version_no"] = case.version_no + 1
        if user_id is not None:
            data["update_user"] = user_id
        result = cls._save_model(ManualTestCase, cls._validate_case(data, case), case)
        if result.instance:
            ManualTestCaseVersionService.record(
                result.instance,
                source=ManualTestCaseVersionSourceEnum.LIBRARY.value,
                changed_by_id=user_id,
            )
            if previous_suite_id:
                ManualTestSuiteService.refresh_stats(previous_suite_id)
            if result.instance.suite_id != previous_suite_id:
                if result.instance.suite_id:
                    ManualTestSuiteService.refresh_stats(result.instance.suite_id)
        return result

    @classmethod
    def normalize_bulk_case_updates(cls, updates) -> tuple[list[dict], dict | None]:
        if not isinstance(updates, list) or not updates or len(updates) > 500:
            return [], {"updates": "批量更新必须包含 1-500 条用例"}
        normalized = []
        seen_ids = set()
        for index, item in enumerate(updates):
            if not isinstance(item, dict):
                return [], {f"updates[{index}]": "更新项必须是对象"}
            try:
                case_id = int(item.get("id"))
                version_no = int(item.get("version_no"))
            except (TypeError, ValueError):
                return [], {f"updates[{index}]": "用例 ID 和版本号必须是整数"}
            changes = item.get("changes")
            if case_id <= 0 or version_no <= 0 or not isinstance(changes, dict) or not changes:
                return [], {f"updates[{index}]": "用例 ID、版本号和修改字段不能为空"}
            invalid_fields = sorted(set(changes) - cls.BULK_EDITABLE_CASE_FIELDS)
            if invalid_fields:
                return [], {f"updates[{index}]": f"不支持批量修改字段：{', '.join(invalid_fields)}"}
            if case_id in seen_ids:
                return [], {f"updates[{index}]": "同一用例在一批请求中只能出现一次"}
            seen_ids.add(case_id)
            normalized.append({"id": case_id, "version_no": version_no, "changes": dict(changes)})
        return normalized, None

    @classmethod
    @transaction.atomic
    def bulk_update_cases(
            cls,
            updates: list[dict],
            user_id: int | None,
    ) -> FunctionalTestMutationResult:
        normalized, errors = cls.normalize_bulk_case_updates(updates)
        if errors:
            return FunctionalTestMutationResult(errors=errors)
        case_map = {
            case.id: case
            for case in ManualTestCase.objects.select_for_update().filter(
                id__in=[item["id"] for item in normalized]
            )
        }
        missing_ids = [item["id"] for item in normalized if item["id"] not in case_map]
        if missing_ids:
            return FunctionalTestMutationResult(errors={"ids": f"用例不存在：{missing_ids}"})
        conflicts = [
            {
                "id": item["id"],
                "expected_version": item["version_no"],
                "current_version": case_map[item["id"]].version_no,
            }
            for item in normalized
            if item["version_no"] != case_map[item["id"]].version_no
        ]
        if conflicts:
            return FunctionalTestMutationResult(data={"conflicts": conflicts})

        prepared = []
        validation_errors = {}
        for item in normalized:
            case = case_map[item["id"]]
            data = dict(item["changes"])
            if "owner_id" in data:
                data["owner"] = data.pop("owner_id")
            if "project_product_id" in data:
                data["project_product"] = data.pop("project_product_id")
            if "module_id" in data:
                data["module"] = data.pop("module_id")
            data["version_no"] = case.version_no + 1
            if user_id is not None:
                data["update_user"] = user_id
            try:
                data = cls._validate_case(data, case)
                validate_model(ManualTestCase, data, instance=case, partial=True)
            except FunctionalTestError as error:
                validation_errors[str(case.id)] = {"row": error.msg}
                continue
            except ModelMutationValidationError as error:
                validation_errors[str(case.id)] = error.errors
                continue
            prepared.append((case, data))
        if validation_errors:
            return FunctionalTestMutationResult(errors=validation_errors)

        suite_ids = set()
        for case, data in prepared:
            previous_suite_id = case.suite_id
            ManualTestCaseVersionService.ensure_baseline(case)
            case = save_model(ManualTestCase, data, instance=case, partial=True)
            ManualTestCaseVersionService.record(
                case,
                source=ManualTestCaseVersionSourceEnum.LIBRARY.value,
                changed_by_id=user_id,
            )
            suite_ids.update(item for item in (previous_suite_id, case.suite_id) if item)
        saved_case_map = {
            case.id: case
            for case in ProductModuleService.with_full_paths(
                ManualTestCase.objects.filter(id__in=[item["id"] for item in normalized]),
                "module",
            ).select_related("project_product__project")
        }
        updated = []
        for item in normalized:
            case = saved_case_map[item["id"]]
            project_product = case.project_product
            project = getattr(project_product, "project", None)
            updated.append({
                "id": case.id,
                "version_no": case.version_no,
                "update_time": case.update_time.strftime("%Y-%m-%d %H:%M:%S"),
                "project_product_id": case.project_product_id,
                "project_product_path": "/".join(filter(None, [
                    getattr(project, "name", None),
                    getattr(project_product, "name", None),
                ])),
                "module_id": case.module_id,
                "module_path": case.module.get_full_path() if case.module_id else "",
            })
        for suite_id in suite_ids:
            ManualTestSuiteService.refresh_stats(suite_id)
        return FunctionalTestMutationResult(data={"updated": updated, "conflicts": []})

    @staticmethod
    @transaction.atomic
    def delete_cases(case_ids: list[int], suite_id: int | None = None) -> dict:
        queryset = ManualTestCase.objects.filter(id__in=case_ids)
        if suite_id is not None:
            queryset = queryset.filter(suite_id=suite_id)
        target_ids = list(queryset.values_list("id", flat=True))
        suite_ids = {item for item in queryset.values_list("suite_id", flat=True) if item}
        protected_ids = set(
            queryset.filter(plan_bindings__isnull=False).values_list("id", flat=True)
        ) | set(queryset.filter(defect_relations__isnull=False).values_list("id", flat=True))
        if protected_ids:
            raise FunctionalTestError(FUNCTIONAL_TEST_CASE_PLAN_EXECUTION_DELETE_NOT_ALLOWED,
                                      value=(", ".join(str(item) for item in sorted(protected_ids)),),
                                      )
        deleted_ids = list(queryset.values_list("id", flat=True))
        queryset.delete()
        for current_suite_id in suite_ids:
            ManualTestSuiteService.refresh_stats(current_suite_id)
        return {
            "deleted_case_ids": deleted_ids,
            "deleted_count": len(deleted_ids),
            "suite_ids": sorted(suite_ids),
            "ignored_case_ids": [item for item in case_ids if item not in target_ids],
        }

    @staticmethod
    def _validate_context_resource(payload: dict):
        if payload.get("url_type") == FunctionalTestContextUrlTypeEnum.FEISHU.value:
            raise FunctionalTestError(FUNCTIONAL_TEST_TYPE_SAVE_INVALID)

    @classmethod
    @transaction.atomic
    def create_context_resource(
            cls,
            payload: dict,
            user_id: int | None,
    ) -> FunctionalTestMutationResult:
        data = dict(payload)
        cls._validate_context_resource(data)
        if user_id is not None:
            data["create_user"] = user_id
            data["update_user"] = user_id
        if data.get("context_key") == FunctionalTestContextKeyEnum.PLATFORM_CASE.value:
            raise FunctionalTestError(FUNCTIONAL_TEST_DATABASE_CASE_NOT_ALLOWED)
        return cls._save_model(FunctionalTestContextResource, data)

    @classmethod
    @transaction.atomic
    def update_context_resource(
            cls,
            resource_id: int,
            payload: dict,
            user_id: int | None,
    ) -> FunctionalTestMutationResult:
        resource = FunctionalTestContextResource.objects.get(id=resource_id)
        data = dict(payload)
        cls._validate_context_resource(data)
        if user_id is not None:
            data["update_user"] = user_id
        if data.get("context_key") == FunctionalTestContextKeyEnum.PLATFORM_CASE.value:
            raise FunctionalTestError(FUNCTIONAL_TEST_DATABASE_CASE_NOT_ALLOWED)
        return cls._save_model(FunctionalTestContextResource, data, resource)

    @staticmethod
    @transaction.atomic
    def delete_context_resources(resource_ids: list[int]) -> dict:
        queryset = FunctionalTestContextResource.objects.filter(id__in=resource_ids)
        deleted_ids = list(queryset.values_list("id", flat=True))
        suite_ids = sorted(set(queryset.values_list("suite_id", flat=True)))
        queryset.delete()
        return {
            "deleted_resource_ids": deleted_ids,
            "deleted_count": len(deleted_ids),
            "suite_ids": suite_ids,
        }
