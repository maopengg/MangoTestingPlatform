# -*- coding: utf-8 -*-
from src.apps.ai.exceptions import ai_service_error
from src.apps.ai.models import AiAgentArtifact, AiAgentTask
from src.apps.ai.services.agent.context import AgentContextService
from src.apps.ai.services.core import AiTaskService
from src.apps.ai.services.harness.artifact import AgentArtifactService
from src.apps.functional_test.enums import ManualTestAutomationTypeEnum, ManualTestTypeEnum
from src.apps.functional_test.models import ManualTestSuite
from src.apps.functional_test.selectors.querysets import FunctionalTestQuerySelector


class ApiAutomationLookupMixin:
    @classmethod
    def find_active_task(cls, manual_case_id: int) -> AiAgentTask | None:
        queryset = AiAgentTask.objects.filter(
            task_type=cls.task_type,
            status__in=cls.active_statuses,
        ).order_by("-id")
        for task in queryset[:200]:
            input_data = task.input_data or {}
            is_same_single = input_data.get("manual_case_id") == manual_case_id
            is_same_batch = input_data.get("mode") == "batch" and manual_case_id in (
                    input_data.get("manual_case_ids") or [])
            if is_same_single or is_same_batch:
                task = AiTaskService.reconcile_interrupted_task(task)
                if task.status in cls.active_statuses:
                    return task
        return None

    @classmethod
    def find_active_suite_batch_task(cls, suite_id: int) -> AiAgentTask | None:
        queryset = AiAgentTask.objects.filter(
            task_type=cls.task_type,
            status__in=cls.active_statuses,
        ).order_by("-id")
        for task in queryset[:200]:
            input_data = task.input_data or {}
            if input_data.get("mode") == "batch" and str(input_data.get("suite_id") or "") == str(suite_id):
                task = AiTaskService.reconcile_interrupted_task(task)
                if task.status in cls.active_statuses:
                    return task
        return None

    @classmethod
    def resolve_batch_cases(cls, suite_id: int | None = None, manual_case_ids: list | None = None,
                            scope: str | None = None):
        normalized_ids = cls.normalize_manual_case_ids(manual_case_ids)
        queryset = FunctionalTestQuerySelector.manual_test_case().select_related("suite", "project_product", "module")
        if normalized_ids:
            cases = list(queryset.filter(id__in=normalized_ids))
            case_map = {case.id: case for case in cases}
            cases = [case_map[case_id] for case_id in normalized_ids if case_id in case_map]
            cases = [case for case in cases if ManualTestTypeEnum.API.value in (case.test_types or [])]
            suite_ids = {case.suite_id for case in cases}
            if suite_id:
                cases = [case for case in cases if str(case.suite_id) == str(suite_id)]
                suite_ids = {case.suite_id for case in cases}
            if len(suite_ids) > 1:
                raise ai_service_error("批量生成API自动化只能选择同一个需求下的用例")
            if not cases:
                raise ai_service_error("当前选择中没有可生成API自动化的用例")
            return cases[0].suite, cases
        if not suite_id:
            raise ai_service_error("请选择要批量生成API自动化的需求")
        cases_queryset = queryset.filter(suite_id=suite_id,
                                         test_types__contains=[ManualTestTypeEnum.API.value]).order_by("id")
        if scope == "unbound_api_cases":
            bound_case_ids = FunctionalTestQuerySelector.manual_test_automation_binding().filter(
                manual_case__suite_id=suite_id,
                automation_type=ManualTestAutomationTypeEnum.API.value,
            ).values_list("manual_case_id", flat=True)
            cases_queryset = cases_queryset.exclude(id__in=bound_case_ids)
        cases = list(cases_queryset)
        if not cases:
            suite = FunctionalTestQuerySelector.manual_test_suite().filter(id=suite_id).first()
            if suite:
                return suite, []
            raise ai_service_error("当前需求暂无可生成API自动化的用例")
        return cases[0].suite, cases

    @staticmethod
    def attach_context_snapshot(task: AiAgentTask, context_package: dict):
        artifact = AgentArtifactService.create(
            task,
            "api_context_snapshot",
            context_package,
            status="validated",
        )
        task.input_data = {**(task.input_data or {}), "context_artifact_id": artifact.id}
        task.input_snapshot = task.input_data
        task.save(update_fields=["input_data", "input_snapshot", "update_time"])

    @staticmethod
    def load_context_snapshot(task: AiAgentTask, suite: ManualTestSuite) -> dict:
        artifact_id = (task.input_data or {}).get("context_artifact_id")
        artifact = AiAgentArtifact.objects.filter(
            id=artifact_id,
            task=task,
            artifact_type="api_context_snapshot",
        ).first()
        if artifact:
            return artifact.content_json or {}
        return AgentContextService.build_api_context_package(
            suite,
            (task.input_data or {}).get("selected_context_keys") or None,
        )

    @staticmethod
    def normalize_manual_case_ids(values: list | tuple | None = None) -> list[int]:
        if values is None:
            return []
        if not isinstance(values, (list, tuple, set)):
            values = [values]
        normalized = []
        for value in values:
            try:
                case_id = int(value)
            except (TypeError, ValueError):
                continue
            if case_id and case_id not in normalized:
                normalized.append(case_id)
        return normalized
