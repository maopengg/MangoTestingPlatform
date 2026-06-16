# -*- coding: utf-8 -*-
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.ai.models import AiAgentTask, AiAgentTaskStep, AiAgentToolCall
from src.apps.ai.agent.api_automation.agent import ApiAutomationAgent
from src.apps.ai.agent.functional_case.agent import FunctionalCaseAgent
from src.apps.ai.views.skill import AiSkillSerializer
from src.apps.user.views.user import UserSerializers
from src.common.enums.ai_enum import AiAgentTaskTypeEnum
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class AiAgentTaskSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = AiAgentTask
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("skill", "create_user")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["skill"] = AiSkillSerializer(instance=instance.skill).data if instance.skill_id else None
        data["create_user"] = UserSerializers(instance=instance.create_user).data if instance.create_user_id else None
        return data


class AiAgentTaskCRUD(ModelCRUD):
    model = AiAgentTask
    queryset = AiAgentTask.objects.all()
    serializer_class = AiAgentTaskSerializer
    serializer = AiAgentTaskSerializer
    not_matching_str = ModelCRUD.not_matching_str + ["skill", "status"]


class AiAgentTaskViews(ViewSet):
    model = AiAgentTask
    serializer_class = AiAgentTaskSerializer

    @action(methods=["get"], detail=False)
    @error_response("system")
    def task_detail(self, request: Request):
        from src.apps.ai.views.agent_task_step import AiAgentTaskStepSerializer
        from src.apps.ai.views.agent_tool_call import AiAgentToolCallSerializer

        task = AiAgentTask.objects.get(id=request.query_params.get("id"))
        data = AiAgentTaskSerializer(instance=task).data
        data["steps"] = AiAgentTaskStepSerializer(instance=AiAgentTaskStep.objects.filter(task=task), many=True).data
        data["tool_calls"] = AiAgentToolCallSerializer(instance=AiAgentToolCall.objects.filter(task=task), many=True).data
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def tool_call(self, request: Request):
        from src.apps.ai.views.agent_tool_call import AiAgentToolCallSerializer

        queryset = AiAgentToolCall.objects.all()
        task_id = request.query_params.get("task_id")
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        return ResponseData.success(RESPONSE_MSG_0001, AiAgentToolCallSerializer(instance=queryset, many=True).data, queryset.count())

    @action(methods=["get"], detail=False)
    @error_response("system")
    def step(self, request: Request):
        from src.apps.ai.views.agent_task_step import AiAgentTaskStepSerializer

        queryset = AiAgentTaskStep.objects.all()
        task_id = request.query_params.get("task_id")
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        return ResponseData.success(RESPONSE_MSG_0001, AiAgentTaskStepSerializer(instance=queryset, many=True).data, queryset.count())

    @action(methods=["post"], detail=False)
    @error_response("system")
    def retry(self, request: Request):
        task = AiAgentTask.objects.get(id=request.data.get("id"))
        if task.task_type == AiAgentTaskTypeEnum.MANUAL_CASE_SYNC.value:
            try:
                task = FunctionalCaseAgent.retry(task.id)
            except ValueError as exc:
                return ResponseData.fail(RESPONSE_MSG_0185, str(exc))
            return ResponseData.success(RESPONSE_MSG_0178, AiAgentTaskSerializer(instance=task).data)
        if task.task_type == AiAgentTaskTypeEnum.GENERATE_API_CASE.value:
            try:
                task = ApiAutomationAgent.retry(task.id)
            except ValueError as exc:
                return ResponseData.fail(RESPONSE_MSG_0185, str(exc))
            return ResponseData.success(RESPONSE_MSG_0178, AiAgentTaskSerializer(instance=task).data)
        return ResponseData.fail(RESPONSE_MSG_0186)

    @staticmethod
    def request_user_id(request: Request) -> int | None:
        return request.user.get("id") if isinstance(request.user, dict) else None

    @action(methods=["post"], detail=False)
    @error_response("system")
    def functional_case_start(self, request: Request):
        try:
            task = FunctionalCaseAgent.start(
                suite_id=request.data.get("suite_id"),
                context_keys=request.data.get("context_keys") or None,
                skill_id=request.data.get("skill_id") or None,
                ai_role=request.data.get("ai_role") or None,
                deep_check=bool(request.data.get("deep_check")),
                user_instruction=request.data.get("user_instruction") or "",
                user_id=self.request_user_id(request),
            )
        except ValueError as exc:
            return ResponseData.fail(RESPONSE_MSG_0185, str(exc))
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
        from src.apps.ai.views.agent_task_step import AiAgentTaskStepSerializer

        task_id = request.query_params.get("task_id") or request.query_params.get("id")
        steps = FunctionalCaseAgent.steps(task_id)
        return ResponseData.success(RESPONSE_MSG_0001, AiAgentTaskStepSerializer(instance=steps, many=True).data, steps.count())

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
        try:
            task = ApiAutomationAgent.start(
                manual_case_id=request.data.get("manual_case_id") or request.data.get("case_id"),
                suite_id=request.data.get("suite_id") or None,
                manual_case_ids=request.data.get("manual_case_ids") or None,
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
            return ResponseData.fail(RESPONSE_MSG_0171, str(exc))
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
        from src.apps.ai.views.agent_task_step import AiAgentTaskStepSerializer

        task_id = request.query_params.get("task_id") or request.query_params.get("id")
        steps = ApiAutomationAgent.steps(task_id)
        return ResponseData.success(RESPONSE_MSG_0001, AiAgentTaskStepSerializer(instance=steps, many=True).data, steps.count())

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
            return ResponseData.fail(RESPONSE_MSG_0171, str(exc))
        return ResponseData.success(RESPONSE_MSG_0178, AiAgentTaskSerializer(instance=task).data)
