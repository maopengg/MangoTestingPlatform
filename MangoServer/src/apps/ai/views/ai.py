# -*- coding: utf-8 -*-
import json

from django.forms import model_to_dict
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.ai.models import AiAgentContext, AiAgentTask, AiAgentTaskStep, AiAgentToolCall, AiAssistantMessage, AiAssistantSession, AiMcpServer, AiMcpTool, AiSkill
from src.apps.ai.service.assistant import AiAssistantService
from src.apps.ai.service.core import McpService, SkillService, mask_sensitive
from src.apps.system.service.ai.client import AiConfigError
from src.common.enums.ai_enum import AiAgentTaskTypeEnum, AiSkillStatusEnum
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class AiSkillSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = AiSkill
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("user")

    @staticmethod
    def get_user_name(instance):
        return instance.user.name if instance.user else ""


class AiMcpServerSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    last_sync_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    last_test_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    is_builtin = serializers.SerializerMethodField()
    is_builtin_local = serializers.SerializerMethodField()
    is_builtin_manual = serializers.SerializerMethodField()
    is_connected = serializers.SerializerMethodField()

    class Meta:
        model = AiMcpServer
        fields = "__all__"

    def validate_prompt(self, value):
        if not str(value or "").strip():
            raise serializers.ValidationError("MCP使用提示词不能为空")
        return str(value).strip()

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("create_user", "update_user")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["auth_config"] = mask_sensitive(data.get("auth_config") or {})
        return data

    @staticmethod
    def get_is_builtin(instance):
        return bool((instance.auth_config or {}).get("builtin"))

    @staticmethod
    def get_is_builtin_local(instance):
        return bool((instance.auth_config or {}).get("builtin_local"))

    @staticmethod
    def get_is_builtin_manual(instance):
        return bool((instance.auth_config or {}).get("builtin_manual"))

    @staticmethod
    def get_is_connected(instance):
        return bool(instance.last_test_time and not instance.last_error)


class AiMcpToolSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = AiMcpTool
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("server")


class AiAgentTaskSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = AiAgentTask
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("skill", "create_user")


class AiAgentToolCallSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = AiAgentToolCall
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("task", "server")


class AiAgentTaskStepSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    start_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    end_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = AiAgentTaskStep
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("task")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["input_data"] = mask_sensitive(data.get("input_data") or {})
        data["output_data"] = mask_sensitive(data.get("output_data") or {})
        return data


class AiAgentContextSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    task_no = serializers.CharField(source="task.task_no", read_only=True)

    class Meta:
        model = AiAgentContext
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("task", "create_user")


class AiAssistantSessionSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = AiAssistantSession
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("create_user")


class AiAssistantMessageSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    need_confirm = serializers.SerializerMethodField()

    class Meta:
        model = AiAssistantMessage
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("session")

    @staticmethod
    def get_need_confirm(instance):
        return bool((instance.metadata or {}).get("need_confirm"))

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["tool_arguments"] = mask_sensitive(data.get("tool_arguments") or {})
        data["tool_result"] = mask_sensitive(data.get("tool_result") or {})
        data["metadata"] = mask_sensitive(data.get("metadata") or {})
        return data


class AiSkillCRUD(ModelCRUD):
    model = AiSkill
    queryset = AiSkill.objects.all()
    serializer_class = AiSkillSerializer
    serializer = AiSkillSerializer

    @error_response("system")
    def post(self, request: Request):
        data = dict(request.data)
        data.setdefault("status", AiSkillStatusEnum.PUBLISHED.value)
        data.setdefault("user", request.user.get("id") if isinstance(request.user, dict) else None)
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)

    @error_response("system")
    def put(self, request: Request):
        data = dict(request.data)
        return super().put(data)


class AiSkillViews(ViewSet):
    @action(methods=["post"], detail=False)
    @error_response("system")
    def publish(self, request: Request):
        skill = AiSkill.objects.get(id=request.data.get("id"))
        data = AiSkillSerializer(instance=SkillService.publish(skill)).data
        return ResponseData.success(RESPONSE_MSG_0082, data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def disable(self, request: Request):
        skill = AiSkill.objects.get(id=request.data.get("id"))
        skill.status = AiSkillStatusEnum.DISABLED.value
        skill.save(update_fields=["status", "update_time"])
        return ResponseData.success(RESPONSE_MSG_0082, AiSkillSerializer(instance=skill).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def archive(self, request: Request):
        skill = AiSkill.objects.get(id=request.data.get("id"))
        skill.status = AiSkillStatusEnum.ARCHIVED.value
        skill.save(update_fields=["status", "update_time"])
        return ResponseData.success(RESPONSE_MSG_0082, AiSkillSerializer(instance=skill).data)


class AiMcpServerCRUD(ModelCRUD):
    model = AiMcpServer
    queryset = AiMcpServer.objects.all()
    serializer_class = AiMcpServerSerializer
    serializer = AiMcpServerSerializer

    @error_response("system")
    def get(self, request: Request):
        McpService.ensure_builtin_server(request)
        queryset = self.serializer.setup_eager_loading(AiMcpServer.objects.all())
        McpService.refresh_statuses(queryset, McpService.request_user_id(request))
        return ResponseData.success(RESPONSE_MSG_0001, self.serializer(instance=queryset, many=True).data, queryset.count())

    @error_response("system")
    def post(self, request: Request):
        data = dict(request.data)
        data["create_user"] = request.user.get("id") if isinstance(request.user, dict) else None
        data["update_user"] = request.user.get("id") if isinstance(request.user, dict) else None
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)

    @error_response("system")
    def put(self, request: Request):
        data = dict(request.data)
        auth_config = data.get("auth_config")
        if isinstance(auth_config, dict) and data.get("id"):
            old_config = AiMcpServer.objects.filter(id=data.get("id")).values_list("auth_config", flat=True).first() or {}
            merged_config = dict(old_config)
            for key, value in auth_config.items():
                if value == "***":
                    continue
                merged_config[key] = value
            data["auth_config"] = merged_config
        data["update_user"] = request.user.get("id") if isinstance(request.user, dict) else None
        return super().put(data)


class AiMcpServerViews(ViewSet):
    @action(methods=["post"], detail=False)
    @error_response("system")
    def test(self, request: Request):
        server = AiMcpServer.objects.get(id=request.data.get("id"))
        return ResponseData.success(RESPONSE_MSG_0035, McpService.test_server(server, McpService.request_user_id(request)))

    @action(methods=["post"], detail=False)
    @error_response("system")
    def refresh_status(self, request: Request):
        McpService.ensure_builtin_server(request)
        queryset = AiMcpServerSerializer.setup_eager_loading(AiMcpServer.objects.all())
        McpService.refresh_statuses(queryset, McpService.request_user_id(request))
        return ResponseData.success(RESPONSE_MSG_0035, AiMcpServerSerializer(instance=queryset, many=True).data, queryset.count())

    @action(methods=["post"], detail=False)
    @error_response("system")
    def builtin(self, request: Request):
        server = AiMcpServer.objects.get(id=request.data.get("id"))
        is_builtin = bool(request.data.get("is_builtin"))
        return ResponseData.success(RESPONSE_MSG_0082, AiMcpServerSerializer(instance=McpService.set_builtin(server, is_builtin)).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def sync_tools(self, request: Request):
        server = AiMcpServer.objects.get(id=request.data.get("id"))
        user_id = McpService.request_user_id(request)
        result = McpService.test_server(server, user_id)
        if not result.get("ok"):
            return ResponseData.fail(RESPONSE_MSG_0003, result)
        return ResponseData.success(RESPONSE_MSG_0035, McpService.sync_tools(server, user_id))


class AiMcpToolCRUD(ModelCRUD):
    model = AiMcpTool
    queryset = AiMcpTool.objects.all()
    serializer_class = AiMcpToolSerializer
    serializer = AiMcpToolSerializer
    not_matching_str = ModelCRUD.not_matching_str + ["server", "risk_level", "enabled", "require_confirm"]


class AiMcpToolViews(ViewSet):
    @action(methods=["put"], detail=False)
    @error_response("system")
    def status(self, request: Request):
        tool = AiMcpTool.objects.get(id=request.data.get("id"))
        for field in ("enabled", "require_confirm", "risk_level"):
            if field in request.data:
                setattr(tool, field, request.data.get(field))
        tool.save()
        return ResponseData.success(RESPONSE_MSG_0082, AiMcpToolSerializer(instance=tool).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def call(self, request: Request):
        tool = AiMcpTool.objects.select_related("server").get(id=request.data.get("id"))
        if tool.tool_type != "tool":
            return ResponseData.fail(RESPONSE_MSG_0003, "只有 MCP tool 支持直接调用")
        if not tool.enabled:
            return ResponseData.fail(RESPONSE_MSG_0003, "该 MCP tool 已停用")
        try:
            result = McpService.call_tool(tool.server, tool.name, request.data.get("arguments") or {}, McpService.request_user_id(request))
        except Exception as exc:
            return ResponseData.fail(RESPONSE_MSG_0003, str(exc))
        return ResponseData.success(RESPONSE_MSG_0168, result)


class AiAgentTaskCRUD(ModelCRUD):
    model = AiAgentTask
    queryset = AiAgentTask.objects.all()
    serializer_class = AiAgentTaskSerializer
    serializer = AiAgentTaskSerializer
    not_matching_str = ModelCRUD.not_matching_str + ["skill", "status"]


class AiAgentTaskViews(ViewSet):
    @action(methods=["get"], detail=False)
    @error_response("system")
    def task_detail(self, request: Request):
        task = AiAgentTask.objects.get(id=request.query_params.get("id"))
        data = AiAgentTaskSerializer(instance=task).data
        data["steps"] = AiAgentTaskStepSerializer(
            instance=AiAgentTaskStep.objects.filter(task=task),
            many=True,
        ).data
        data["tool_calls"] = AiAgentToolCallSerializer(
            instance=AiAgentToolCall.objects.filter(task=task),
            many=True,
        ).data
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def tool_call(self, request: Request):
        queryset = AiAgentToolCall.objects.all()
        task_id = request.query_params.get("task_id")
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        return ResponseData.success(RESPONSE_MSG_0001, AiAgentToolCallSerializer(instance=queryset, many=True).data, queryset.count())

    @action(methods=["get"], detail=False)
    @error_response("system")
    def step(self, request: Request):
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
            from src.apps.ai.agent.functional_case.agent import FunctionalCaseAgent

            try:
                task = FunctionalCaseAgent.retry(task.id)
            except ValueError as exc:
                return ResponseData.fail(RESPONSE_MSG_0185, str(exc))
            return ResponseData.success(RESPONSE_MSG_0178, AiAgentTaskSerializer(instance=task).data)
        if task.task_type == AiAgentTaskTypeEnum.GENERATE_API_CASE.value:
            from src.apps.ai.agent.api_automation.agent import ApiAutomationAgent

            try:
                task = ApiAutomationAgent.retry(task.id)
            except ValueError as exc:
                return ResponseData.fail(RESPONSE_MSG_0185, str(exc))
            return ResponseData.success(RESPONSE_MSG_0178, AiAgentTaskSerializer(instance=task).data)
        return ResponseData.fail(RESPONSE_MSG_0186)


class AiAgentContextCRUD(ModelCRUD):
    model = AiAgentContext
    queryset = AiAgentContext.objects.all()
    serializer_class = AiAgentContextSerializer
    serializer = AiAgentContextSerializer
    not_matching_str = ModelCRUD.not_matching_str + ["suite_id", "manual_case_id", "context_type", "context_hash", "task"]


class AiAssistantViews(ViewSet):
    @action(methods=["get"], detail=False)
    @error_response("system")
    def status(self, request: Request):
        return ResponseData.success(
            RESPONSE_MSG_0001,
            AiAssistantService.builtin_status(request, preferred_server_id=request.query_params.get("mcp_server_id")),
        )

    @action(methods=["get"], detail=False)
    @error_response("system")
    def session(self, request: Request):
        session = AiAssistantService.get_or_create_session(request, session_id=request.query_params.get("id"))
        return ResponseData.success(RESPONSE_MSG_0001, AiAssistantSessionSerializer(instance=session).data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def sessions(self, request: Request):
        queryset = AiAssistantService.list_sessions(request)
        return ResponseData.success(RESPONSE_MSG_0001, AiAssistantSessionSerializer(instance=queryset, many=True).data, queryset.count())

    @action(methods=["post"], detail=False)
    @error_response("system")
    def create_session(self, request: Request):
        session = AiAssistantService.create_session(
            request,
            page_context=request.data.get("page_context") or {},
            title=request.data.get("title") or "",
        )
        return ResponseData.success(RESPONSE_MSG_0184, AiAssistantSessionSerializer(instance=session).data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def messages(self, request: Request):
        session = AiAssistantService.get_or_create_session(request, session_id=request.query_params.get("session_id"))
        queryset = AiAssistantService.messages(session)
        return ResponseData.success(RESPONSE_MSG_0001, AiAssistantMessageSerializer(instance=queryset, many=True).data, queryset.count())

    @action(methods=["post"], detail=False)
    @error_response("system")
    def message(self, request: Request):
        content = (request.data.get("content") or "").strip()
        if not content:
            return ResponseData.fail(RESPONSE_MSG_0182)
        try:
            data = AiAssistantService.chat(
                request,
                content,
                session_id=request.data.get("session_id"),
                page_context=request.data.get("page_context") or {},
                mcp_server_id=request.data.get("mcp_server_id"),
            )
        except AiConfigError as exc:
            return ResponseData.fail((RESPONSE_MSG_0177[0], RESPONSE_MSG_0177[1].format(str(exc))))
        if not data.get("mcp_online"):
            return ResponseData.fail(RESPONSE_MSG_0179, data)
        return ResponseData.success(RESPONSE_MSG_0180, data)

    @action(methods=["post"], detail=False)
    def message_stream(self, request: Request):
        content = (request.data.get("content") or "").strip()

        def event_stream():
            if not content:
                yield f"event: error\ndata: {json.dumps({'message': RESPONSE_MSG_0182[1]}, ensure_ascii=False)}\n\n"
                return
            try:
                for event in AiAssistantService.stream_chat(
                    request,
                    content,
                    session_id=request.data.get("session_id"),
                    page_context=request.data.get("page_context") or {},
                    mcp_server_id=request.data.get("mcp_server_id"),
                ):
                    yield (
                        f"event: {event.get('event', 'message')}\n"
                        f"data: {json.dumps(event.get('data') or {}, ensure_ascii=False)}\n\n"
                    )
            except AiConfigError as exc:
                yield f"event: error\ndata: {json.dumps({'message': RESPONSE_MSG_0177[1].format(str(exc))}, ensure_ascii=False)}\n\n"
            except Exception as exc:
                yield f"event: error\ndata: {json.dumps({'message': str(exc)}, ensure_ascii=False)}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    @action(methods=["post"], detail=False)
    @error_response("system")
    def tool_confirm(self, request: Request):
        try:
            data = AiAssistantService.confirm_tool(request, request.data.get("message_id"))
        except AiConfigError as exc:
            return ResponseData.fail((RESPONSE_MSG_0177[0], RESPONSE_MSG_0177[1].format(str(exc))))
        if not data.get("mcp_online"):
            return ResponseData.fail(RESPONSE_MSG_0179, data)
        return ResponseData.success(RESPONSE_MSG_0180, data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def clear(self, request: Request):
        AiAssistantService.clear_session(request, request.data.get("session_id"))
        return ResponseData.success(RESPONSE_MSG_0181)
