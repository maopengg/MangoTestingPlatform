# -*- coding: utf-8 -*-
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.ai.agent.api_automation.agent import ApiAutomationAgent
from src.apps.ai.agent.functional_case.agent import FunctionalCaseAgent
from src.apps.ai.api.serializers.agent_task import AiAgentTaskSerializer, AiAgentArtifactSerializer, \
    AiAgentEventSerializer, AiAgentEvaluationSerializer
from src.apps.ai.enums import AiAgentTaskStatusEnum
from src.apps.ai.enums import AiAgentTaskTypeEnum
from src.apps.ai.models import (
    AiAgentArtifact,
    AiAgentEvent,
    AiAgentEvaluation,
    AiAgentTask,
    AiAgentTaskItem,
    AiAgentTaskStep,
    AiAgentToolCall,
)
from src.apps.ai.services.agent_task_mutation import AiAgentTaskMutationService
from src.apps.functional_test.selectors.access_scope import (
    filter_manual_case_by_data_scope,
    filter_manual_suite_by_data_scope,
)
from src.apps.functional_test.selectors.querysets import FunctionalTestQuerySelector
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    AI_OPERATION_FAILED,
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0082,
    RESPONSE_MSG_0171,
    RESPONSE_MSG_0178,
    RESPONSE_MSG_0185,
    RESPONSE_MSG_0186,
    RESPONSE_MSG_0187,
    RESPONSE_MSG_0188,
    RESPONSE_MSG_0210,
)


class AiAgentTaskCRUD(ModelCRUD):
    model = AiAgentTask
    queryset = AiAgentTask.objects.all()
    serializer_class = AiAgentTaskSerializer
    serializer = AiAgentTaskSerializer
    page_permission_key = 'ai.task'
    not_matching_str = ModelCRUD.not_matching_str + ["skill", "status"]


class AiAgentTaskViews(ViewSet):
    model = AiAgentTask
    serializer_class = AiAgentTaskSerializer
    action_permission_map = {
        'functional_case_start': 'ai.task:execute',
        'api_automation_start': 'ai.task:execute',
        'task_detail': 'ai.task:detail',
        'tool_call': 'ai.task:detail',
        'step': 'ai.task:detail',
        'retry': 'ai.task:retry',
        'run_detail': 'ai.task:detail',
        'run_steps': 'ai.task:detail',
        'run_artifacts': 'ai.task:detail',
        'run_evidence': 'ai.task:detail',
        'run_events': 'ai.task:detail',
        'run_cancel': 'ai.task:retry',
        'run_confirm': 'ai.task:retry',
    }

    @action(methods=["get"], detail=False)
    @error_response("system")
    def task_detail(self, request: Request):
        from src.apps.ai.api.serializers.agent_task_step import AiAgentTaskStepSerializer
        from src.apps.ai.api.serializers.agent_tool_call import AiAgentToolCallSerializer

        task = AiAgentTask.objects.get(id=request.query_params.get("id"))
        data = AiAgentTaskSerializer(instance=task).data
        data["steps"] = AiAgentTaskStepSerializer(instance=AiAgentTaskStep.objects.filter(task=task), many=True).data
        data["tool_calls"] = AiAgentToolCallSerializer(instance=AiAgentToolCall.objects.filter(task=task),
                                                       many=True).data
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def run_detail(self, request: Request):
        task = AiAgentTask.objects.get(id=request.query_params.get("id") or request.query_params.get("task_id"))
        data = AiAgentTaskSerializer(instance=task).data
        data["item_count"] = AiAgentTaskItem.objects.filter(task=task).count()
        data["evaluation_count"] = AiAgentEvaluation.objects.filter(task=task).count()
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def run_steps(self, request: Request):
        from src.apps.ai.api.serializers.agent_task_step import AiAgentTaskStepSerializer

        queryset = AiAgentTaskStep.objects.filter(
            task_id=request.query_params.get("task_id") or request.query_params.get("id"))
        return ResponseData.success(RESPONSE_MSG_0001, AiAgentTaskStepSerializer(queryset, many=True).data,
                                    queryset.count())

    @action(methods=["get"], detail=False)
    @error_response("system")
    def run_artifacts(self, request: Request):
        task_id = request.query_params.get("task_id") or request.query_params.get("id")
        queryset = AiAgentArtifact.objects.filter(task_id=task_id)
        artifact_type = request.query_params.get("artifact_type")
        if artifact_type:
            queryset = queryset.filter(artifact_type=artifact_type)
        return ResponseData.success(RESPONSE_MSG_0001, AiAgentArtifactSerializer(queryset, many=True).data,
                                    queryset.count())

    @action(methods=["get"], detail=False)
    @error_response("system")
    def run_evidence(self, request: Request):
        task = AiAgentTask.objects.get(
            id=request.query_params.get("task_id") or request.query_params.get("id")
        )
        steps = AiAgentTaskStep.objects.filter(task=task).order_by("step_order", "id")
        artifacts = AiAgentArtifact.objects.filter(task=task).order_by("id")
        evaluations = AiAgentEvaluation.objects.filter(task=task).order_by("id")
        return ResponseData.success(
            RESPONSE_MSG_0001,
            {
                "task": {
                    "id": task.id,
                    "agent_key": task.agent_key,
                    "agent_version": task.agent_version,
                    "model_snapshot": task.model_snapshot or {},
                    "mcp_snapshot": task.mcp_snapshot or {},
                    "skill_version_id": task.skill_version_id,
                    "context_hash": task.context_hash,
                },
                "steps": [
                    {
                        "step_key": item.step_key,
                        "step_name": item.step_name,
                        "status": item.status,
                        "progress": item.progress,
                        "attempt_no": item.attempt_no,
                        "error_category": item.error_category,
                        "error_message": item.error_message,
                    }
                    for item in steps
                ],
                "artifacts": [
                    {
                        "id": item.id,
                        "artifact_type": item.artifact_type,
                        "status": item.status,
                        "schema_version": item.schema_version,
                        "content_hash": item.content_hash,
                        "task_item_id": item.task_item_id,
                    }
                    for item in artifacts
                ],
                "evaluations": AiAgentEvaluationSerializer(evaluations, many=True).data,
            },
        )

    @action(methods=["get"], detail=False)
    @error_response("system")
    def run_events(self, request: Request):
        task_id = request.query_params.get("task_id") or request.query_params.get("id")
        after_id = request.query_params.get("after_id") or 0
        queryset = AiAgentEvent.objects.filter(task_id=task_id, id__gt=after_id).order_by("id")[:200]
        return ResponseData.success(RESPONSE_MSG_0001, AiAgentEventSerializer(queryset, many=True).data, len(queryset))

    @action(methods=["post"], detail=False)
    @error_response("system")
    def run_cancel(self, request: Request):
        task = AiAgentTask.objects.get(id=request.data.get("id") or request.data.get("task_id"))
        if task.status in [AiAgentTaskStatusEnum.SUCCESS.value, AiAgentTaskStatusEnum.FAIL.value,
                           AiAgentTaskStatusEnum.CANCELLED.value]:
            return ResponseData.fail(RESPONSE_MSG_0185, "当前任务已结束")
        AiAgentTaskMutationService.cancel(task)
        return ResponseData.success(RESPONSE_MSG_0082, AiAgentTaskSerializer(task).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def run_confirm(self, request: Request):
        task = AiAgentTask.objects.get(id=request.data.get("id") or request.data.get("task_id"))
        if task.status != AiAgentTaskStatusEnum.WAITING_CONFIRM.value:
            return ResponseData.fail(RESPONSE_MSG_0185, "当前任务不在等待确认状态")
        confirmation = request.data.get("confirmation") or {}
        if not str(confirmation.get("answer") or "").strip():
            return ResponseData.fail(RESPONSE_MSG_0185, "请填写对关键需求歧义的确认说明")
        AiAgentTaskMutationService.confirm(task, confirmation)
        return ResponseData.success(RESPONSE_MSG_0082, AiAgentTaskSerializer(task).data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def tool_call(self, request: Request):
        from src.apps.ai.api.serializers.agent_tool_call import AiAgentToolCallSerializer

        queryset = AiAgentToolCall.objects.all()
        task_id = request.query_params.get("task_id")
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        return ResponseData.success(RESPONSE_MSG_0001, AiAgentToolCallSerializer(instance=queryset, many=True).data,
                                    queryset.count())

    @action(methods=["get"], detail=False)
    @error_response("system")
    def step(self, request: Request):
        from src.apps.ai.api.serializers.agent_task_step import AiAgentTaskStepSerializer

        queryset = AiAgentTaskStep.objects.all()
        task_id = request.query_params.get("task_id")
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        return ResponseData.success(RESPONSE_MSG_0001, AiAgentTaskStepSerializer(instance=queryset, many=True).data,
                                    queryset.count())

    @action(methods=["post"], detail=False)
    @error_response("system")
    def retry(self, request: Request):
        task = AiAgentTask.objects.get(id=request.data.get("id"))
        if task.task_type == AiAgentTaskTypeEnum.MANUAL_CASE_SYNC.value:
            try:
                task = FunctionalCaseAgent.retry(task.id)
            except ValueError as exc:
                return ResponseData.fail(AI_OPERATION_FAILED)
            return ResponseData.success(RESPONSE_MSG_0178, AiAgentTaskSerializer(instance=task).data)
        if task.task_type == AiAgentTaskTypeEnum.GENERATE_API_CASE.value:
            try:
                task = ApiAutomationAgent.retry(task.id)
            except ValueError as exc:
                return ResponseData.fail(AI_OPERATION_FAILED)
            return ResponseData.success(RESPONSE_MSG_0178, AiAgentTaskSerializer(instance=task).data)
        return ResponseData.fail(RESPONSE_MSG_0186)

    @staticmethod
    def request_user_id(request: Request) -> int | None:
        return request.user.get("id") if isinstance(request.user, dict) else None

    @action(methods=["post"], detail=False)
    @error_response("system")
    def functional_case_start(self, request: Request):
        suite_id = request.data.get("suite_id")
        scoped_suites = filter_manual_suite_by_data_scope(request,
                                                          FunctionalTestQuerySelector.manual_test_suite().all())
        if not scoped_suites.filter(id=suite_id).exists():
            return ResponseData.fail(RESPONSE_MSG_0210)
        try:
            task = FunctionalCaseAgent.start(
                suite_id=suite_id,
                context_keys=request.data.get("context_keys") or None,
                current_resource_ids=(
                    request.data.get("current_resource_ids")
                    if "current_resource_ids" in request.data
                    else None
                ),
                historical_context=request.data.get("historical_context") or None,
                skill_id=request.data.get("skill_id") or None,
                ai_role=request.data.get("ai_role") or None,
                deep_check=bool(request.data.get("deep_check")),
                user_instruction=request.data.get("user_instruction") or "",
                user_id=self.request_user_id(request),
            )
        except ValueError as exc:
            return ResponseData.fail(AI_OPERATION_FAILED)
        return ResponseData.success(RESPONSE_MSG_0178, AiAgentTaskSerializer(instance=task).data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def functional_case_status(self, request: Request):
        task = FunctionalCaseAgent.status(
            request.query_params.get("id") or None,
            suite_id=request.query_params.get("suite_id") or None,
        )
        return ResponseData.success(RESPONSE_MSG_0001, AiAgentTaskSerializer(instance=task).data if task else None)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def functional_case_steps(self, request: Request):
        from src.apps.ai.api.serializers.agent_task_step import AiAgentTaskStepSerializer

        task_id = request.query_params.get("task_id") or request.query_params.get("id")
        steps = FunctionalCaseAgent.steps(task_id)
        return ResponseData.success(RESPONSE_MSG_0001, AiAgentTaskStepSerializer(instance=steps, many=True).data,
                                    steps.count())

    @action(methods=["post"], detail=False)
    @error_response("system")
    def functional_case_retry(self, request: Request):
        input_patch = {
            key: value
            for key, value in {
                "selected_context_keys": request.data.get("context_keys"),
                "ai_role": request.data.get("ai_role"),
                "deep_check": request.data.get("deep_check"),
                "user_instruction": request.data.get("user_instruction"),
                "current_resource_ids": request.data.get("current_resource_ids"),
                "historical_context": request.data.get("historical_context"),
            }.items()
            if value is not None
        }
        if "skill_id" in request.data:
            input_patch["skill_id"] = request.data.get("skill_id") or None
        task = FunctionalCaseAgent.retry(request.data.get("id"), input_patch)
        return ResponseData.success(RESPONSE_MSG_0178, AiAgentTaskSerializer(instance=task).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def api_automation_start(self, request: Request):
        suite_id = request.data.get("suite_id") or None
        manual_case_id = request.data.get("manual_case_id") or request.data.get("case_id")
        manual_case_ids = request.data.get("manual_case_ids") or []
        scoped_cases = filter_manual_case_by_data_scope(request, FunctionalTestQuerySelector.manual_test_case().all())
        try:
            requested_case_ids = {
                int(item)
                for item in ([manual_case_id] if manual_case_id else []) + list(manual_case_ids)
            }
        except (TypeError, ValueError):
            return ResponseData.fail(RESPONSE_MSG_0171, "功能用例 ID 格式不正确")
        if requested_case_ids and scoped_cases.filter(id__in=requested_case_ids).count() != len(requested_case_ids):
            return ResponseData.fail(RESPONSE_MSG_0210)
        if suite_id:
            scoped_suites = filter_manual_suite_by_data_scope(request,
                                                              FunctionalTestQuerySelector.manual_test_suite().all())
            if not scoped_suites.filter(id=suite_id).exists():
                return ResponseData.fail(RESPONSE_MSG_0210)
        try:
            task = ApiAutomationAgent.start(
                manual_case_id=manual_case_id,
                suite_id=suite_id,
                manual_case_ids=manual_case_ids or None,
                scope=request.data.get("scope") or None,
                context_keys=request.data.get("context_keys") or None,
                skill_id=request.data.get("skill_id") or None,
                mcp_server_ids=request.data.get("mcp_server_ids") or None,
                ai_role=request.data.get("ai_role") or None,
                user_instruction=request.data.get("user_instruction") or "",
                user_id=self.request_user_id(request),
            )
        except ValueError as exc:
            if str(exc) == "api_generation_options_required":
                return ResponseData.fail(RESPONSE_MSG_0187)
            if str(exc) == "api_generation_task_running":
                return ResponseData.fail(RESPONSE_MSG_0188)
            return ResponseData.fail(AI_OPERATION_FAILED)
        return ResponseData.success(RESPONSE_MSG_0178, AiAgentTaskSerializer(instance=task).data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def api_automation_status(self, request: Request):
        task = ApiAutomationAgent.status(
            request.query_params.get("id") or None,
            suite_id=request.query_params.get("suite_id") or None,
            manual_case_id=request.query_params.get("manual_case_id") or request.query_params.get("case_id") or None,
        )
        return ResponseData.success(RESPONSE_MSG_0001, AiAgentTaskSerializer(instance=task).data if task else None)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def api_automation_steps(self, request: Request):
        from src.apps.ai.api.serializers.agent_task_step import AiAgentTaskStepSerializer

        task_id = request.query_params.get("task_id") or request.query_params.get("id")
        steps = ApiAutomationAgent.steps(task_id)
        return ResponseData.success(RESPONSE_MSG_0001, AiAgentTaskStepSerializer(instance=steps, many=True).data,
                                    steps.count())

    @action(methods=["post"], detail=False)
    @error_response("system")
    def api_automation_retry(self, request: Request):
        try:
            task = ApiAutomationAgent.retry(
                request.data.get("id"),
                {
                    key: value
                    for key, value in {
                    "selected_context_keys": request.data.get("context_keys"),
                    "skill_id": request.data.get("skill_id"),
                    "mcp_server_ids": request.data.get("mcp_server_ids"),
                    "ai_role": request.data.get("ai_role"),
                    "user_instruction": request.data.get("user_instruction"),
                }.items()
                    if value is not None
                },
            )
        except ValueError as exc:
            return ResponseData.fail(AI_OPERATION_FAILED)
        return ResponseData.success(RESPONSE_MSG_0178, AiAgentTaskSerializer(instance=task).data)
