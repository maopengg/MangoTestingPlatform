# -*- coding: utf-8 -*-
from django.db import transaction
from django.utils import timezone

from src.apps.functional_test.enums import (
    FunctionalTestPlanScopeTypeEnum,
    FunctionalTestDefectSourceEnum,
    FunctionalTestDefectStatusEnum,
)
from src.apps.functional_test.exceptions import (
    FUNCTIONAL_TEST_CASE_REQUIRED,
    FUNCTIONAL_TEST_STEP_DEFECT_INVALID,
    FUNCTIONAL_TEST_DEFECT_DUPLICATED,
    FUNCTIONAL_TEST_DEFECT_INVALID,
    FUNCTIONAL_TEST_DEFECT_DISABLED,
    FUNCTIONAL_TEST_CASE_PLAN_DEFECT_RELATION_MINIMUM_REQUIRED,
    FUNCTIONAL_TEST_PROJECT_PRODUCT_CASE_DEFECT_RELATION_INVALID,
    FUNCTIONAL_TEST_DEFECT_STATUS_EXECUTION_NOT_ALLOWED,
    FUNCTIONAL_TEST_PROJECT_PRODUCT_REQUIREMENT_DEFECT_RELATION_INVALID,
    FunctionalTestError,
)
from src.apps.functional_test.models import (
    FunctionalTestDefect,
    FunctionalTestDefectCase,
    FunctionalTestPlan,
    FunctionalTestPlanCase,
    ManualTestCase,
    ManualTestSuite,
)
from src.apps.functional_test.services.execution import FunctionalTestExecutionService
from src.apps.functional_test.services.suite import ManualTestSuiteService
from src.apps.test_center.models import FileData


class FunctionalTestDefectService:
    STATUS_TRANSITIONS = {
        FunctionalTestDefectStatusEnum.NEW.value: {
            FunctionalTestDefectStatusEnum.CONFIRMED.value,
        },
        FunctionalTestDefectStatusEnum.CONFIRMED.value: {
            FunctionalTestDefectStatusEnum.PROCESSING.value,
        },
        FunctionalTestDefectStatusEnum.PROCESSING.value: {
            FunctionalTestDefectStatusEnum.RESOLVED.value,
        },
        FunctionalTestDefectStatusEnum.RESOLVED.value: {
            FunctionalTestDefectStatusEnum.CLOSED.value,
            FunctionalTestDefectStatusEnum.REOPENED.value,
        },
        FunctionalTestDefectStatusEnum.REOPENED.value: {
            FunctionalTestDefectStatusEnum.PROCESSING.value,
            FunctionalTestDefectStatusEnum.RESOLVED.value,
        },
        FunctionalTestDefectStatusEnum.CLOSED.value: {
            FunctionalTestDefectStatusEnum.REOPENED.value,
        },
    }

    @staticmethod
    def validate_reproduce_steps(steps):
        if not isinstance(steps, list) or any(
                not isinstance(item, dict)
                or not isinstance(item.get("sort"), int)
                or not item.get("action")
                for item in steps
        ):
            raise FunctionalTestError(FUNCTIONAL_TEST_STEP_DEFECT_INVALID)

    @staticmethod
    def validate_attachment_ids(file_ids, project_product_id=None):
        if not isinstance(file_ids, list) or any(
                not isinstance(item, int) or isinstance(item, bool) or item <= 0 for item in file_ids
        ) or len(file_ids) != len(set(file_ids)):
            raise FunctionalTestError(FUNCTIONAL_TEST_DEFECT_DUPLICATED)
        if file_ids:
            files = FileData.objects.filter(id__in=file_ids)
            if files.count() != len(file_ids):
                raise FunctionalTestError(FUNCTIONAL_TEST_DEFECT_DUPLICATED)
            if project_product_id and files.exclude(
                    project_product_id__in=[project_product_id, None],
            ).exists():
                raise FunctionalTestError(FUNCTIONAL_TEST_DEFECT_DUPLICATED)

    @classmethod
    def validate_payload(cls, payload: dict, instance: FunctionalTestDefect | None = None):
        project_product_id = payload.get("project_product") or getattr(instance, "project_product_id", None)
        module_id = payload.get("module") if "module" in payload else getattr(instance, "module_id", None)
        ManualTestSuiteService.validate_module_product(project_product_id, module_id)
        requirement_version_id = (
            payload.get("requirement_version")
            if "requirement_version" in payload
            else getattr(instance, "requirement_version_id", None)
        )
        if requirement_version_id and not ManualTestSuite.objects.filter(
                id=requirement_version_id, project_product_id=project_product_id,
        ).exists():
            raise FunctionalTestError(FUNCTIONAL_TEST_PROJECT_PRODUCT_REQUIREMENT_DEFECT_RELATION_INVALID)
        if "reproduce_steps" in payload:
            cls.validate_reproduce_steps(payload.get("reproduce_steps"))
        if "attachment_file_ids" in payload:
            cls.validate_attachment_ids(payload.get("attachment_file_ids"), project_product_id)

    @staticmethod
    def validate_relations(project_product_id: int, case_ids: list[int], plan_case_ids: list[int]):
        cases = list(ManualTestCase.objects.filter(id__in=case_ids))
        plan_cases = list(
            FunctionalTestPlanCase.objects.filter(id__in=plan_case_ids)
            .select_related("case", "plan")
        )
        if len(cases) != len(set(case_ids)) or len(plan_cases) != len(set(plan_case_ids)):
            raise FunctionalTestError(FUNCTIONAL_TEST_PROJECT_PRODUCT_CASE_DEFECT_RELATION_INVALID)
        if any(item.project_product_id != project_product_id for item in cases):
            raise FunctionalTestError(FUNCTIONAL_TEST_PROJECT_PRODUCT_CASE_DEFECT_RELATION_INVALID)
        if any(
                item.case.project_product_id != project_product_id or item.plan.project_product_id != project_product_id
                for item in plan_cases
        ):
            raise FunctionalTestError(FUNCTIONAL_TEST_PROJECT_PRODUCT_CASE_DEFECT_RELATION_INVALID)
        return cases, plan_cases

    @classmethod
    def replace_relations(cls, defect: FunctionalTestDefect, case_ids=None, plan_case_ids=None):
        case_ids = list(dict.fromkeys(int(item) for item in (case_ids or []) if str(item).isdigit()))
        plan_case_ids = list(dict.fromkeys(int(item) for item in (plan_case_ids or []) if str(item).isdigit()))
        cases, plan_cases = cls.validate_relations(defect.project_product_id, case_ids, plan_case_ids)
        if defect.source_type == FunctionalTestDefectSourceEnum.PLAN.value and not plan_cases:
            raise FunctionalTestError(FUNCTIONAL_TEST_CASE_PLAN_DEFECT_RELATION_MINIMUM_REQUIRED)
        defect.case_relations.all().delete()
        FunctionalTestDefectCase.objects.bulk_create(
            [FunctionalTestDefectCase(defect=defect, case=item) for item in cases]
            + [FunctionalTestDefectCase(defect=defect, plan_case=item) for item in plan_cases]
        )

    @classmethod
    @transaction.atomic
    def bind_relations(cls, defect: FunctionalTestDefect, case_ids=None, plan_case_ids=None) -> int:
        case_ids = list(dict.fromkeys(int(item) for item in (case_ids or []) if str(item).isdigit()))
        plan_case_ids = list(dict.fromkeys(int(item) for item in (plan_case_ids or []) if str(item).isdigit()))
        cases, plan_cases = cls.validate_relations(defect.project_product_id, case_ids, plan_case_ids)
        existing_case_ids = set(
            defect.case_relations.filter(case_id__in=case_ids).values_list("case_id", flat=True)
        )
        existing_plan_case_ids = set(
            defect.case_relations.filter(plan_case_id__in=plan_case_ids).values_list("plan_case_id", flat=True)
        )
        relations = [
                        FunctionalTestDefectCase(defect=defect, case=item)
                        for item in cases if item.id not in existing_case_ids
                    ] + [
                        FunctionalTestDefectCase(defect=defect, plan_case=item)
                        for item in plan_cases if item.id not in existing_plan_case_ids
                    ]
        FunctionalTestDefectCase.objects.bulk_create(relations)
        return len(relations)

    @staticmethod
    @transaction.atomic
    def unbind_relations(
            defect: FunctionalTestDefect,
            *,
            relation_ids=None,
            case_ids=None,
            plan_case_ids=None,
    ) -> int:
        queryset = defect.case_relations.all()
        filters = None
        from django.db.models import Q

        for condition in (
                Q(id__in=relation_ids or []) if relation_ids else None,
                Q(case_id__in=case_ids or []) if case_ids else None,
                Q(plan_case_id__in=plan_case_ids or []) if plan_case_ids else None,
        ):
            if condition is not None:
                filters = condition if filters is None else filters | condition
        if filters is None:
            return 0
        deleted, _ = queryset.filter(filters).delete()
        return deleted

    @classmethod
    @transaction.atomic
    def create_retest_plan(cls, defect: FunctionalTestDefect, payload: dict, user_id: int | None):
        relations = defect.case_relations.select_related("case", "plan_case__case")
        case_ids = []
        for relation in relations:
            case_id = relation.case_id or relation.plan_case.case_id
            if case_id not in case_ids:
                case_ids.append(case_id)
        if not case_ids:
            raise FunctionalTestError(FUNCTIONAL_TEST_CASE_REQUIRED)
        owner_id = payload.get("owner") or user_id
        plan = FunctionalTestPlan.objects.create(
            name=payload.get("name") or f"{defect.defect_no} 缺陷验证",
            project_product_id=defect.project_product_id,
            scope_type=FunctionalTestPlanScopeTypeEnum.REGRESSION.value,
            scope_ref=defect.defect_no,
            environment=payload.get("environment") or defect.environment,
            build_version=payload.get("build_version"),
            owner_id=owner_id,
            update_user_id=user_id,
            planned_start_time=payload.get("planned_start_time"),
            planned_end_time=payload.get("planned_end_time"),
            remark=payload.get("remark") or f"用于验证缺陷 {defect.defect_no}",
        )
        FunctionalTestExecutionService.add_plan_cases(plan.id, case_ids)
        return plan

    @classmethod
    @transaction.atomic
    def create(cls, serializer, payload: dict, user_id: int | None):
        cls.validate_payload(payload)
        serializer.validated_data.pop("case_ids", None)
        serializer.validated_data.pop("plan_case_ids", None)
        defect = serializer.save(reporter_id=user_id, update_user_id=user_id)
        cls.replace_relations(defect, payload.get("case_ids"), payload.get("plan_case_ids"))
        return defect

    @classmethod
    @transaction.atomic
    def update(cls, serializer, payload: dict, user_id: int | None):
        cls.validate_payload(payload, serializer.instance)
        serializer.validated_data.pop("case_ids", None)
        serializer.validated_data.pop("plan_case_ids", None)
        defect = serializer.save(update_user_id=user_id)
        current_case_ids = list(
            defect.case_relations.filter(case__isnull=False).values_list("case_id", flat=True)
        )
        current_plan_case_ids = list(
            defect.case_relations.filter(plan_case__isnull=False).values_list("plan_case_id", flat=True)
        )
        cls.replace_relations(
            defect,
            payload.get("case_ids", current_case_ids),
            payload.get("plan_case_ids", current_plan_case_ids),
        )
        return defect

    @classmethod
    @transaction.atomic
    def transition(cls, defect: FunctionalTestDefect, target_status: int, payload: dict, user_id: int | None):
        if target_status not in cls.STATUS_TRANSITIONS.get(defect.status, set()):
            raise FunctionalTestError(FUNCTIONAL_TEST_DEFECT_STATUS_EXECUTION_NOT_ALLOWED)
        assignee_id = payload.get("assignee") or defect.assignee_id
        resolution = payload.get("resolution", defect.resolution)
        if target_status == FunctionalTestDefectStatusEnum.PROCESSING.value and not assignee_id:
            raise FunctionalTestError(FUNCTIONAL_TEST_DEFECT_INVALID)
        if target_status in (
                FunctionalTestDefectStatusEnum.RESOLVED.value,
                FunctionalTestDefectStatusEnum.CLOSED.value,
        ) and resolution is None:
            raise FunctionalTestError(FUNCTIONAL_TEST_DEFECT_DISABLED)
        now = timezone.now()
        defect.status = target_status
        defect.assignee_id = assignee_id
        defect.resolution = resolution
        defect.resolution_note = payload.get("resolution_note", defect.resolution_note)
        defect.update_user_id = user_id
        if target_status == FunctionalTestDefectStatusEnum.RESOLVED.value:
            defect.resolved_at = now
        if target_status == FunctionalTestDefectStatusEnum.CLOSED.value:
            defect.closed_at = now
        elif target_status == FunctionalTestDefectStatusEnum.REOPENED.value:
            defect.closed_at = None
        defect.save()
        return defect
