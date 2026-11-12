# -*- coding: utf-8 -*-
from django.db import transaction
from django.db.models import Count, Max, Q
from django.utils import timezone

from src.apps.auto_api.enums import ApiCaseScenarioLayerEnum, ApiCaseScenarioTypeEnum
from src.apps.functional_test.enums import (
    FunctionalRequirementSelfTestStatusEnum,
    FunctionalRequirementTaskStatusEnum,
    FunctionalRequirementTaskTypeEnum,
    FunctionalTestContextContentTypeEnum,
    FunctionalTestContextParseStatusEnum,
    FunctionalTestPlanStatusEnum,
    ManualTestCaseVersionSourceEnum,
    ManualTestSuiteStatusEnum,
    ManualTestChangeStatusEnum,
    ManualTestOptimizeStatusEnum,
    ManualTestTypeEnum,
)
from src.apps.functional_test.exceptions import (
    FUNCTIONAL_TEST_PROJECT_PRODUCT_MODULE_INVALID,
    FUNCTIONAL_TEST_PROJECT_PRODUCT_VERSION_REQUIREMENT_INVALID,
    FUNCTIONAL_TEST_VERSION_REQUIREMENT_INVALID,
    FUNCTIONAL_TEST_VERSION_REQUIREMENT_NOT_ALLOWED,
    FUNCTIONAL_TEST_REQUIREMENT_NOT_FOUND,
    FUNCTIONAL_TEST_CASE_INVALID,
    FUNCTIONAL_TEST_MODULE_REQUIREMENT_REQUIRED,
    FUNCTIONAL_TEST_VERSION_REQUIREMENT_ITERATION_BINDING_INVALID,
    FUNCTIONAL_TEST_REQUIREMENT_STATUS_INVALID,
    FUNCTIONAL_TEST_PLAN_RELATION_MINIMUM_REQUIRED,
    FUNCTIONAL_TEST_PLAN_REQUIREMENT_EXECUTION_NOT_ALLOWED,
    FUNCTIONAL_TEST_REQUIREMENT_STATUS_INVALID_CODE_REQUIREMENT_STATUS_INVALID,
    FUNCTIONAL_TEST_REQUIREMENT_INVALID,
    FUNCTIONAL_TEST_PLAN_INVALID,
    FUNCTIONAL_TEST_TASK_CREATE_MINIMUM_REQUIRED,
    FUNCTIONAL_TEST_TASK_INVALID,
    FUNCTIONAL_TEST_PLAN_INVALID_CODE_PLAN_INVALID,
    FunctionalTestError,
)
from src.apps.functional_test.models import (
    FunctionalRequirementCase,
    FunctionalRequirementTask,
    FunctionalTestIteration,
    FunctionalTestRequirement,
    ManualTestAutomationBinding,
    ManualTestCase,
    ManualTestSuite,
)
from src.apps.functional_test.services.cases.case_version import ManualTestCaseVersionService
from src.apps.functional_test.services.cases.common import ManualTestValidationService, _hash_text
from src.apps.functional_test.services.requirements.iteration import FunctionalTestIterationService
from src.apps.test_center.enums import CaseLevelEnum
from src.apps.test_center.models import ProductModule, ProjectProduct


class ManualTestSuiteService:
    GENERATED_CASE_NO_PREFIX = "FT"

    @classmethod
    @transaction.atomic
    def create_version(
            cls,
            previous: ManualTestSuite,
            validated_data: dict,
            user_id: int | None,
    ) -> ManualTestSuite:
        suite = ManualTestSuite.objects.create(**validated_data)
        FunctionalRequirementTask.objects.bulk_create([
            FunctionalRequirementTask(
                requirement_version=suite,
                name=item.name,
                task_type=item.task_type,
                status=FunctionalRequirementTaskStatusEnum.PENDING.value,
                owner=item.owner,
                planned_start_date=item.planned_start_date,
                planned_end_date=item.planned_end_date,
                sort_order=item.sort_order,
                estimated_person_days=item.estimated_person_days,
                self_test_status=FunctionalRequirementSelfTestStatusEnum.NOT_STARTED.value,
                remark=item.remark,
                update_user_id=user_id,
            )
            for item in previous.requirement_tasks.all()
        ])
        FunctionalRequirementCase.objects.bulk_create([
            FunctionalRequirementCase(
                requirement_version=suite,
                case=binding.case,
                bound_case_version=binding.case.version_no,
                sort_order=binding.sort_order,
                create_user_id=user_id,
            )
            for binding in previous.case_bindings.select_related("case")
        ])
        cls.refresh_stats(suite.id)
        return suite

    @classmethod
    def confirm_submit(cls, suite: ManualTestSuite, user_id: int | None) -> ManualTestSuite:
        FunctionalTestIterationService.validate_schedule(
            iteration=suite.iteration_ref,
            development_owner_id=suite.development_owner_id,
            planned_start_date=suite.planned_start_date,
            planned_submit_date=suite.planned_submit_date,
            status=ManualTestSuiteStatusEnum.PENDING_TEST.value,
        )
        suite.status = ManualTestSuiteStatusEnum.PENDING_TEST.value
        suite.actual_submit_at = timezone.now()
        suite.update_user_id = user_id
        suite.save(update_fields=["status", "actual_submit_at", "update_user", "update_time"])
        return suite

    @classmethod
    @transaction.atomic
    def unlink_cases(cls, suite: ManualTestSuite, cases, user_id: int | None) -> list[int]:
        case_ids = []
        for case in cases.select_for_update():
            case_ids.append(case.id)
            ManualTestCaseVersionService.ensure_baseline(case)
            case.suite_id = None
            case.version_no += 1
            case.update_user_id = user_id
            case.save(update_fields=["suite", "version_no", "update_user", "update_time"])
            ManualTestCaseVersionService.record(
                case,
                source=ManualTestCaseVersionSourceEnum.LIBRARY.value,
                changed_by_id=user_id,
            )
        cls.refresh_stats(suite.id)
        return case_ids

    @classmethod
    @transaction.atomic
    def transition_status(
            cls,
            suite_id: int,
            target_status: int,
            user_id: int | None,
            expected_update_time: str | None = None,
    ) -> tuple[ManualTestSuite, list[str]]:
        suite = ManualTestSuite.objects.select_for_update().select_related("iteration_ref").get(id=suite_id)
        if target_status not in ManualTestSuiteStatusEnum.get_key_list():
            raise FunctionalTestError(FUNCTIONAL_TEST_REQUIREMENT_STATUS_INVALID_CODE_REQUIREMENT_STATUS_INVALID)
        if expected_update_time and suite.update_time.strftime("%Y-%m-%d %H:%M:%S") != expected_update_time:
            raise FunctionalTestError(FUNCTIONAL_TEST_REQUIREMENT_STATUS_INVALID)
        if not suite.iteration_ref_id:
            raise FunctionalTestError(FUNCTIONAL_TEST_VERSION_REQUIREMENT_ITERATION_BINDING_INVALID)

        if target_status == ManualTestSuiteStatusEnum.SCHEDULED.value and (
                not suite.description
                or not suite.requirement_id
                or not suite.requirement.owner_id
                or suite.requirement.requirement_category is None
        ):
            raise FunctionalTestError(FUNCTIONAL_TEST_REQUIREMENT_INVALID)
        if target_status == ManualTestSuiteStatusEnum.PENDING_DEVELOPMENT.value and (
                not suite.development_owner_id or not suite.planned_start_date or not suite.planned_submit_date
        ):
            raise FunctionalTestError(FUNCTIONAL_TEST_PLAN_INVALID)

        development_task_types = {
            FunctionalRequirementTaskTypeEnum.FRONTEND.value,
            FunctionalRequirementTaskTypeEnum.BACKEND.value,
            FunctionalRequirementTaskTypeEnum.DATA.value,
            FunctionalRequirementTaskTypeEnum.INTEGRATION.value,
        }
        development_tasks = suite.requirement_tasks.filter(
            task_type__in=development_task_types,
        ).exclude(status=FunctionalRequirementTaskStatusEnum.CANCELLED.value)
        if target_status == ManualTestSuiteStatusEnum.DEVELOPING.value and not development_tasks.exists():
            raise FunctionalTestError(FUNCTIONAL_TEST_TASK_CREATE_MINIMUM_REQUIRED)
        if target_status == ManualTestSuiteStatusEnum.PENDING_TEST.value and (
                not development_tasks.exists()
                or development_tasks.exclude(
            status=FunctionalRequirementTaskStatusEnum.COMPLETED.value,
            self_test_status__in=[
                FunctionalRequirementSelfTestStatusEnum.PASSED.value,
                FunctionalRequirementSelfTestStatusEnum.NOT_APPLICABLE.value,
            ],
        ).exists()
        ):
            raise FunctionalTestError(FUNCTIONAL_TEST_TASK_INVALID)
        if target_status == ManualTestSuiteStatusEnum.PENDING_RELEASE.value and not suite.planned_release_date:
            raise FunctionalTestError(FUNCTIONAL_TEST_PLAN_INVALID_CODE_PLAN_INVALID)

        FunctionalTestIterationService.validate_schedule(
            iteration=suite.iteration_ref,
            development_owner_id=suite.development_owner_id,
            planned_start_date=suite.planned_start_date,
            planned_submit_date=suite.planned_submit_date,
            status=target_status,
            allow_existing_iteration=True,
        )
        if target_status == ManualTestSuiteStatusEnum.TESTING.value:
            started_statuses = {
                FunctionalTestPlanStatusEnum.RUNNING.value,
                FunctionalTestPlanStatusEnum.COMPLETED.value,
                FunctionalTestPlanStatusEnum.CLOSED.value,
            }
            if not suite.test_plans.filter(status__in=started_statuses).exists():
                raise FunctionalTestError(FUNCTIONAL_TEST_PLAN_RELATION_MINIMUM_REQUIRED)
        if (
                target_status == ManualTestSuiteStatusEnum.TEST_COMPLETED.value
                and suite.test_plans.filter(status=FunctionalTestPlanStatusEnum.RUNNING.value).exists()
        ):
            raise FunctionalTestError(FUNCTIONAL_TEST_PLAN_REQUIREMENT_EXECUTION_NOT_ALLOWED)

        update_fields = ["status", "update_user", "update_time"]
        suite.status = target_status
        suite.update_user_id = user_id
        if target_status == ManualTestSuiteStatusEnum.PENDING_TEST.value and not suite.actual_submit_at:
            suite.actual_submit_at = timezone.now()
            update_fields.append("actual_submit_at")
        if target_status == ManualTestSuiteStatusEnum.RELEASED.value and not suite.actual_release_at:
            suite.actual_release_at = timezone.now()
            update_fields.append("actual_release_at")
        suite.save(update_fields=update_fields)

        warnings = []
        if target_status == ManualTestSuiteStatusEnum.TEST_COMPLETED.value:
            unexecuted = suite.test_plans.filter(plan_cases__result=0).exists()
            open_defects = suite.test_plans.filter(
                plan_cases__defect_relations__defect__status__in=[0, 1, 2, 3, 5]
            ).exists()
            if unexecuted:
                warnings.append("仍有未执行的计划用例")
            if open_defects:
                warnings.append("仍有未关闭缺陷")
        return suite, warnings

    @staticmethod
    def module_scope_ids(module_id: int | None) -> list[int]:
        if not module_id:
            return []
        return list(
            ProductModule.objects.filter(
                Q(id=module_id) | Q(parent_id=module_id) | Q(parent__parent_id=module_id)
            ).values_list("id", flat=True)
        )

    @staticmethod
    def validate_module_product(project_product_id: int, module_id: int | None):
        if not module_id:
            return
        if not ProductModule.objects.filter(id=module_id, project_product_id=project_product_id).exists():
            raise FunctionalTestError(FUNCTIONAL_TEST_PROJECT_PRODUCT_MODULE_INVALID)

    @staticmethod
    def module_path(module: ProductModule | None) -> str:
        names = []
        current = module
        while current:
            names.append(current.name)
            current = current.parent
        return " / ".join(reversed(names))

    @classmethod
    def snapshot_paths(cls, snapshot: dict, source_case=None) -> tuple[str, str]:
        product_id = snapshot.get("project_product_id")
        module_id = snapshot.get("module_id")
        if source_case and source_case.project_product_id == product_id:
            product = source_case.project_product
        else:
            product = ProjectProduct.objects.select_related("project").filter(id=product_id).first()
        if source_case and source_case.module_id == module_id:
            module = source_case.module
        else:
            module = ProductModule.objects.select_related("parent__parent").filter(id=module_id).first()
        product_path = " / ".join(
            filter(None, (getattr(getattr(product, "project", None), "name", None), getattr(product, "name", None)))
        )
        return product_path or "-", cls.module_path(module) or "-"

    @staticmethod
    def validate_previous_version(instance: ManualTestSuite | None, previous: ManualTestSuite):
        if not instance:
            return
        current = previous
        visited = set()
        while current:
            if current.id == instance.id:
                raise FunctionalTestError(FUNCTIONAL_TEST_VERSION_REQUIREMENT_NOT_ALLOWED)
            if current.id in visited:
                raise FunctionalTestError(FUNCTIONAL_TEST_VERSION_REQUIREMENT_NOT_ALLOWED)
            visited.add(current.id)
            current = current.previous_version

    @classmethod
    @transaction.atomic
    def prepare_suite_data(cls, data: dict, user_id: int | None, instance: ManualTestSuite | None = None) -> dict:
        payload = dict(data)
        project_product_id = payload.get("project_product") or getattr(instance, "project_product_id", None)
        module_id = payload.get("module") if "module" in payload else getattr(instance, "module_id", None)
        owner_id = payload.get("owner") or getattr(instance, "owner_id", None)
        requirement_name = payload.get("requirement_name") or getattr(instance, "requirement_name", None)
        if not module_id:
            raise FunctionalTestError(FUNCTIONAL_TEST_MODULE_REQUIREMENT_REQUIRED)
        if project_product_id:
            cls.validate_module_product(int(project_product_id), int(module_id) if module_id else None)

        iteration_id = payload.get("iteration_ref") if "iteration_ref" in payload else getattr(instance,
                                                                                               "iteration_ref_id", None)
        if not iteration_id:
            raise FunctionalTestError(FUNCTIONAL_TEST_VERSION_REQUIREMENT_ITERATION_BINDING_INVALID)
        iteration = None
        if iteration_id:
            iteration = FunctionalTestIteration.objects.filter(id=iteration_id).first()
            if not iteration or iteration.project_product_id != int(project_product_id):
                raise FunctionalTestError(FUNCTIONAL_TEST_PROJECT_PRODUCT_VERSION_REQUIREMENT_INVALID)
        FunctionalTestIterationService.validate_schedule(
            iteration=iteration,
            development_owner_id=(
                payload.get("development_owner")
                if "development_owner" in payload
                else getattr(instance, "development_owner_id", None)
            ),
            planned_start_date=(
                payload.get("planned_start_date")
                if "planned_start_date" in payload
                else getattr(instance, "planned_start_date", None)
            ),
            planned_submit_date=(
                payload.get("planned_submit_date")
                if "planned_submit_date" in payload
                else getattr(instance, "planned_submit_date", None)
            ),
            status=payload.get("status", getattr(instance, "status", 1)),
            allow_existing_iteration=bool(
                instance
                and instance.iteration_ref_id
                and instance.iteration_ref_id == getattr(iteration, "id", None)
            ),
        )

        requirement_id = payload.get("requirement") or getattr(instance, "requirement_id", None)
        if requirement_id:
            requirement = FunctionalTestRequirement.objects.filter(id=requirement_id).first()
            if not requirement:
                raise FunctionalTestError(FUNCTIONAL_TEST_REQUIREMENT_NOT_FOUND)
            if int(project_product_id) != requirement.project_product_id:
                raise FunctionalTestError(FUNCTIONAL_TEST_PROJECT_PRODUCT_VERSION_REQUIREMENT_INVALID)
        else:
            requirement = FunctionalTestRequirement.objects.create(
                name=requirement_name,
                project_product_id=project_product_id,
                owner_id=owner_id,
                update_user_id=user_id,
            )
            payload["requirement"] = requirement.id

        previous_version_id = payload.get("previous_version")
        if previous_version_id:
            previous = ManualTestSuite.objects.select_related("previous_version").get(id=previous_version_id)
            if previous.requirement_id != requirement.id:
                raise FunctionalTestError(FUNCTIONAL_TEST_VERSION_REQUIREMENT_INVALID)
            cls.validate_previous_version(instance, previous)

        if not payload.get("version_no"):
            if instance and instance.version_no:
                payload["version_no"] = instance.version_no
            else:
                current_max = \
                    ManualTestSuite.objects.filter(requirement=requirement).aggregate(value=Max("version_no"))[
                        "value"] or 0
                payload["version_no"] = current_max + 1
        return payload

    @staticmethod
    def module_counts(queryset, project_product_id: int) -> list[dict]:
        modules = list(
            ProductModule.objects.filter(project_product_id=project_product_id)
            .values("id", "parent_id")
            .order_by("sort", "id")
        )
        direct = {
            item["module_id"]: item["count"]
            for item in queryset.filter(project_product_id=project_product_id, module__isnull=False)
            .values("module_id")
            .annotate(count=Count("id"))
        }
        parent_map = {item["id"]: item["parent_id"] for item in modules}
        total = {item["id"]: direct.get(item["id"], 0) for item in modules}
        for module_id, count in direct.items():
            parent_id = parent_map.get(module_id)
            while parent_id:
                total[parent_id] = total.get(parent_id, 0) + count
                parent_id = parent_map.get(parent_id)
        return [
            {
                "module_id": item["id"],
                "direct_count": direct.get(item["id"], 0),
                "total_count": total.get(item["id"], 0),
            }
            for item in modules
        ]

    @staticmethod
    def context_candidates(suite: ManualTestSuite) -> dict:
        from src.apps.functional_test.models import FunctionalTestContextResource

        resource_fields = (
            "id",
            "title",
            "context_key",
            "content_type",
            "parse_status",
            "enabled",
            "update_time",
            "content",
            "extracted_text",
        )

        def serialize_suite(item: ManualTestSuite, relation: str) -> dict:
            resources = list(
                FunctionalTestContextResource.objects.filter(suite=item)
                .values(*resource_fields)
                .order_by("context_key", "id")
            )
            for resource in resources:
                extracted_text = resource.pop("extracted_text", None)
                content = resource.pop("content", None)
                has_text = bool((extracted_text or content or "").strip())
                resource["selectable"] = bool(
                    resource["enabled"]
                    and (
                            resource["content_type"] == FunctionalTestContextContentTypeEnum.TEXT.value
                            or resource["parse_status"] == FunctionalTestContextParseStatusEnum.SUCCESS.value
                    )
                    and has_text
                )
            return {
                "suite_id": item.id,
                "requirement_id": item.requirement_id,
                "requirement_name": item.requirement_name,
                "version_no": item.version_no,
                "iteration": item.iteration,
                "module_id": item.module_id,
                "module_name": item.module.name if item.module_id else None,
                "module_level": item.module.level if item.module_id else None,
                "module_path": ManualTestSuiteService.module_path(item.module),
                "owner_name": item.owner.name if item.owner_id else None,
                "update_time": item.update_time.strftime("%Y-%m-%d %H:%M:%S"),
                "case_count": item.case_count,
                "relation": relation,
                "resource_count": len(resources),
                "resource_counts": {
                    key: len([resource for resource in resources if resource["context_key"] == key])
                    for key in sorted({resource["context_key"] for resource in resources})
                },
                "resources": resources,
            }

        versions = []
        if suite.requirement_id:
            versions = list(
                ManualTestSuite.objects.filter(requirement_id=suite.requirement_id)
                .exclude(id=suite.id)
                .select_related("module", "module__parent", "module__parent__parent", "owner")
                .order_by("-version_no", "-id")
            )
        module_ids = ManualTestSuiteService.module_scope_ids(suite.module_id)
        related = ManualTestSuite.objects.filter(project_product_id=suite.project_product_id)
        if module_ids:
            related = related.filter(module_id__in=module_ids)
        else:
            related = related.none()
        related = list(
            related.exclude(id=suite.id)
            .exclude(requirement_id=suite.requirement_id if suite.requirement_id else -1)
            .select_related("module", "module__parent", "module__parent__parent", "owner")
            .order_by("-update_time")[:100]
        )
        return {
            "current_suite_id": suite.id,
            "requirement_versions": [serialize_suite(item, "requirement_version") for item in versions],
            "module_requirements": [serialize_suite(item, "module_requirement") for item in related],
        }

    @classmethod
    def next_generated_case_no(cls, used_case_numbers: set[str]) -> str:
        index = 1
        while True:
            case_no = f"{cls.GENERATED_CASE_NO_PREFIX}-{index:04d}"
            if case_no not in used_case_numbers:
                used_case_numbers.add(case_no)
                return case_no
            index += 1

    @classmethod
    def assign_ft_case_numbers(cls, cases: list[dict], used_case_numbers: set[str] | None = None) -> list[dict]:
        used = used_case_numbers or set()
        for item in cases:
            item["case_no"] = cls.next_generated_case_no(used)
        return cases

    @staticmethod
    def refresh_stats(suite_id: int):
        bound_case_ids = FunctionalRequirementCase.objects.filter(
            requirement_version_id=suite_id,
        ).values_list("case_id", flat=True)
        legacy_case_ids = ManualTestCase.objects.filter(suite_id=suite_id).values_list("id", flat=True)
        # 关系表上线后仍兼容旧 suite 外键；完成数据迁移前不能让历史用例从统计中消失。
        case_ids = list(set(bound_case_ids).union(legacy_case_ids))
        case_count = len(case_ids)
        automated = (
            ManualTestAutomationBinding.objects.filter(manual_case_id__in=case_ids)
            .values("manual_case_id")
            .distinct()
            .count()
        )
        need_optimize = ManualTestAutomationBinding.objects.filter(
            manual_case_id__in=case_ids,
            optimize_status=ManualTestOptimizeStatusEnum.NEED_OPTIMIZE.value,
        ).count()
        percent = round((automated / case_count * 100) if case_count else 0, 2)
        ManualTestSuite.objects.filter(id=suite_id).update(
            case_count=case_count,
            automated_case_count=automated,
            automation_coverage_percent=percent,
            need_optimize_count=need_optimize,
        )

    @staticmethod
    def normalize_case_scope(suite: ManualTestSuite, item: dict) -> dict:
        item = dict(item or {})
        item["project_product"] = suite.project_product_id
        item["project_product_id"] = suite.project_product_id
        item["module"] = suite.module_id
        item["module_id"] = suite.module_id
        return item

    @staticmethod
    def create_case_from_payload(suite: ManualTestSuite, item: dict, user_id: int | None = None) -> ManualTestCase:
        item = ManualTestSuiteService.normalize_case_scope(suite, item)
        priority = item.get("priority") if item.get(
            "priority") in CaseLevelEnum.get_key_list() else CaseLevelEnum.P1.value
        scenario_layer = item.get("scenario_layer") if item.get(
            "scenario_layer") in ApiCaseScenarioLayerEnum.get_key_list() else ApiCaseScenarioLayerEnum.API.value
        scenario_type = item.get("scenario_type") if item.get(
            "scenario_type") in ApiCaseScenarioTypeEnum.get_key_list() else ApiCaseScenarioTypeEnum.NORMAL.value
        project_product_id = item.get("project_product")
        module_id = item.get("module")
        used_case_numbers = set(
            ManualTestCase.objects.filter(suite=suite)
            .exclude(case_no__isnull=True)
            .exclude(case_no="")
            .values_list("case_no", flat=True)
        )
        case_no = str(item.get("case_no") or "").strip() or ManualTestSuiteService.next_generated_case_no(
            used_case_numbers)
        case = ManualTestCase.objects.create(
            suite=suite,
            project_product_id=project_product_id,
            module_id=module_id,
            case_no=case_no,
            title=item.get("title") or "未命名用例",
            category_level_1=item.get("category_level_1") or None,
            category_level_2=item.get("category_level_2"),
            category_level_3=item.get("category_level_3"),
            priority=priority,
            test_types=item.get("test_types") or [ManualTestTypeEnum.MANUAL.value],
            story_refs=item.get("story_refs") or [],
            precondition=item.get("precondition"),
            test_point=item.get("test_point") or item.get("title") or "未命名测试场景",
            test_steps=item.get("test_steps") or [],
            expected_result=item.get("expected_result"),
            acceptance_source=item.get("acceptance_source"),
            owner_id=item.get("owner") or item.get("owner_id") or suite.owner_id,
            automation_status=item.get("automation_status") or "not_automated",
            scenario_layer=scenario_layer,
            scenario_type=scenario_type,
            scenario_tags=item.get("scenario_tags") or [],
            test_data=item.get("test_data"),
            remark=item.get("remark"),
            source_block_id=item.get("source_block_id"),
            source_text=item.get("source_text"),
            source_hash=item.get("source_hash") or _hash_text(item.get("source_text") or item.get("title")),
        )
        ManualTestCaseVersionService.record(
            case,
            source=ManualTestCaseVersionSourceEnum.REQUIREMENT_SYNC.value,
            changed_by_id=user_id,
        )
        FunctionalRequirementCase.objects.get_or_create(
            requirement_version=suite,
            case=case,
            defaults={"bound_case_version": case.version_no, "create_user_id": user_id},
        )
        ManualTestSuiteService.refresh_stats(suite.id)
        return case

    @classmethod
    def sync_preview(cls, suite: ManualTestSuite, parsed_payload: dict, preserve_case_no: bool = False) -> dict:
        payload = dict(parsed_payload or {})
        payload_suite = dict(payload.get("suite") or {})
        payload_suite.setdefault("requirement_name", suite.requirement_name)
        payload_suite.setdefault("project_product", suite.project_product_id)
        payload_suite.setdefault("module", suite.module_id)
        payload_suite.setdefault("iteration", suite.iteration)
        payload["suite"] = payload_suite
        normalized = ManualTestValidationService.normalize_suite_cases(payload)
        validation_messages = [str(item) for item in normalized.get("errors") or []]
        validation_messages.extend(
            str(item.get("message") or item)
            for item in normalized.get("warnings") or []
            if isinstance(item, dict) and item.get("field")
        )
        if validation_messages:
            raise FunctionalTestError(FUNCTIONAL_TEST_CASE_INVALID,
                                      value=("；".join(validation_messages[:20]),),
                                      )
        current_cases = list(ManualTestCase.objects.filter(suite=suite))
        current_case_numbers = {case.case_no for case in current_cases if case.case_no}
        if not preserve_case_no:
            normalized["cases"] = cls.assign_ft_case_numbers(
                normalized["cases"],
                set(current_case_numbers),
            )
        else:
            used_case_numbers = set(current_case_numbers)
            used_case_numbers.update(item.get("case_no") for item in normalized["cases"] if item.get("case_no"))
            for item in normalized["cases"]:
                if not item.get("case_no"):
                    item["case_no"] = cls.next_generated_case_no(used_case_numbers)
        by_no = {case.case_no: case for case in current_cases if case.case_no}
        by_hash = {case.source_hash: case for case in current_cases if case.source_hash}
        used_case_numbers = {case.case_no for case in current_cases if case.case_no}
        used_case_numbers.update(item.get("case_no") for item in normalized["cases"] if item.get("case_no"))
        matched_ids = set()
        changes = []
        for item in normalized["cases"]:
            item = cls.normalize_case_scope(suite, item)
            target = (
                by_no.get(item.get("case_no")) or by_hash.get(item.get("source_hash"))
                if preserve_case_no
                else by_hash.get(item.get("source_hash"))
            )
            if target and target.case_no:
                item["case_no"] = target.case_no
            if not target and not item.get("case_no"):
                item["case_no"] = cls.next_generated_case_no(used_case_numbers)
            if not target:
                changes.append({"change_status": ManualTestChangeStatusEnum.ADDED.value, "new": item})
                continue
            matched_ids.add(target.id)
            diff_fields = {}
            for field in (
                    "case_no",
                    "project_product_id",
                    "module_id",
                    "title",
                    "category_level_1",
                    "category_level_2",
                    "category_level_3",
                    "test_types",
                    "priority",
                    "precondition",
                    "test_point",
                    "test_steps",
                    "expected_result",
                    "test_data",
                    "scenario_layer",
                    "scenario_type",
                    "scenario_tags",
            ):
                if getattr(target, field) != item.get(field, getattr(target, field)):
                    diff_fields[field] = {"old": getattr(target, field), "new": item.get(field)}
            changes.append(
                {
                    "manual_case_id": target.id,
                    "change_status": ManualTestChangeStatusEnum.CHANGED.value if diff_fields else ManualTestChangeStatusEnum.UNCHANGED.value,
                    "diff_fields": diff_fields,
                    "new": item,
                    "old_title": target.title,
                }
            )
        if preserve_case_no:
            for case in current_cases:
                if case.id not in matched_ids:
                    changes.append(
                        {"manual_case_id": case.id, "change_status": ManualTestChangeStatusEnum.REMOVED.value,
                         "old_title": case.title})
        return {"suite": normalized["suite"], "cases": normalized["cases"], "changes": changes,
                "validation": normalized}
