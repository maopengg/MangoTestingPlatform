# -*- coding: utf-8 -*-
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.ai.agent.api_automation.agent import ApiAutomationAgent
from src.apps.ai.agent.functional_case.agent import FunctionalCaseAgent
from src.apps.ai.agent.task_step import AiAgentTaskStepService
from src.apps.ai.views.ai import AiAgentTaskSerializer, AiAgentTaskStepSerializer
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


def request_user_id(request: Request) -> int | None:
    return request.user.get("id") if isinstance(request.user, dict) else None


class FunctionalCaseAgentViews(ViewSet):
    @action(methods=["post"], detail=False)
    @error_response("system")
    def start(self, request: Request):
        try:
            task = FunctionalCaseAgent.start(
                suite_id=request.data.get("suite_id"),
                context_keys=request.data.get("context_keys") or None,
                skill_id=request.data.get("skill_id") or None,
                ai_role=request.data.get("ai_role") or None,
                deep_check=bool(request.data.get("deep_check")),
                user_instruction=request.data.get("user_instruction") or "",
                user_id=request_user_id(request),
            )
        except ValueError as exc:
            return ResponseData.fail(RESPONSE_MSG_0185, str(exc))
        return ResponseData.success(RESPONSE_MSG_0178, AiAgentTaskSerializer(instance=task).data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def status(self, request: Request):
        task = FunctionalCaseAgent.status(
            request.query_params.get("id") or None,
            suite_id=request.query_params.get("suite_id") or None,
        )
        return ResponseData.success(RESPONSE_MSG_0001, AiAgentTaskSerializer(instance=task).data if task else None)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def steps(self, request: Request):
        task_id = request.query_params.get("task_id") or request.query_params.get("id")
        steps = FunctionalCaseAgent.steps(task_id)
        return ResponseData.success(RESPONSE_MSG_0001, AiAgentTaskStepSerializer(instance=steps, many=True).data, steps.count())

    @action(methods=["post"], detail=False)
    @error_response("system")
    def retry(self, request: Request):
        task = FunctionalCaseAgent.retry(
            request.data.get("id"),
            {
                key: value
                for key, value in {
                    "selected_context_keys": request.data.get("context_keys"),
                    "skill_id": request.data.get("skill_id"),
                    "ai_role": request.data.get("ai_role"),
                    "deep_check": request.data.get("deep_check"),
                    "user_instruction": request.data.get("user_instruction"),
                }.items()
                if value is not None
            },
        )
        return ResponseData.success(RESPONSE_MSG_0178, AiAgentTaskSerializer(instance=task).data)


class ApiAutomationAgentViews(ViewSet):
    @action(methods=["post"], detail=False)
    @error_response("system")
    def start(self, request: Request):
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
                user_id=request_user_id(request),
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
    def status(self, request: Request):
        task = ApiAutomationAgent.status(
            request.query_params.get("id") or None,
            suite_id=request.query_params.get("suite_id") or None,
            manual_case_id=request.query_params.get("manual_case_id") or request.query_params.get("case_id") or None,
        )
        return ResponseData.success(RESPONSE_MSG_0001, AiAgentTaskSerializer(instance=task).data if task else None)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def steps(self, request: Request):
        task_id = request.query_params.get("task_id") or request.query_params.get("id")
        steps = ApiAutomationAgent.steps(task_id)
        return ResponseData.success(RESPONSE_MSG_0001, AiAgentTaskStepSerializer(instance=steps, many=True).data, steps.count())

    @action(methods=["post"], detail=False)
    @error_response("system")
    def retry(self, request: Request):
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
