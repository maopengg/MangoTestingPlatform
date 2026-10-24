# -*- coding: utf-8 -*-
import json
import re
import uuid
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urljoin, urlparse

from django.utils import timezone

from src.apps.ai.enums import (
    AiAgentTaskStatusEnum,
    AiAgentToolCallStatusEnum,
    AiMcpAuthTypeEnum,
    AiMcpStatusEnum,
    AiMcpToolRiskLevelEnum,
    AiMcpTransportTypeEnum,
    AiMcpUseTypeEnum,
    AiSkillStatusEnum,
)
from src.apps.ai.exceptions import ai_service_error
from src.apps.ai.models import AiAgentTask, AiAgentToolCall, AiMcpServer, AiMcpTool, AiMcpToolSnapshot, AiSkill
from src.apps.ai.services.mcp_client import ExternalMcpClient
from src.apps.auto_api.services.api_info.mcp_import import ApiInfoMcpImportService
from src.apps.system.services.ai.client import AiService
from src.common.logging import log
from src.common.prompts import get_prompt

SENSITIVE_KEYS = {"api_key", "authorization", "password", "cookie", "token", "secret"}


def mask_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if str(key).lower() in SENSITIVE_KEYS else mask_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [mask_sensitive(item) for item in value]
    return value


def extract_ai_json(response: dict, *, task=None) -> dict:
    choices = response.get("choices") or []
    if not choices:
        return {}
    message = choices[0].get("message") or {}
    content = message.get("content") or "{}"
    if isinstance(content, dict):
        return content
    return parse_ai_json_content(str(content), task=task)


def parse_ai_json_content(content: str, *, allow_ai_repair: bool = True, task=None) -> dict:
    json_content = extract_json_text(content)
    try:
        return json.loads(json_content)
    except json.JSONDecodeError as exc:
        if not allow_ai_repair:
            raise
        return repair_ai_json_content(json_content, exc, task=task)


def extract_json_text(content: str) -> str:
    text = (content or "{}").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start: end + 1]
    return text


def repair_ai_json_content(content: str, error: json.JSONDecodeError, *, task=None) -> dict:
    prompt = get_prompt("ai.json_repair")
    repair_messages = [
        {"role": "system", "content": prompt.system},
        {
            "role": "user",
            "content": prompt.render(
                "user",
                error_message=error.msg,
                line=error.lineno,
                column=error.colno,
                content=content[:120000],
            ),
        },
    ]
    if task:
        from src.apps.ai.model_gateway.client import AgentModelGateway

        repaired_response = AgentModelGateway.json_chat(
            task=task,
            messages=repair_messages,
            max_tokens=16000,
        )
    else:
        repaired_response = AiService.json_chat(repair_messages, max_tokens=16000)
    choices = repaired_response.get("choices") or []
    if not choices:
        raise ai_service_error(f"AI返回的JSON格式不正确，且自动修复失败：{error.msg}")
    repaired_content = choices[0].get("message", {}).get("content") or "{}"
    if isinstance(repaired_content, dict):
        return repaired_content
    try:
        return parse_ai_json_content(str(repaired_content), allow_ai_repair=False, task=task)
    except json.JSONDecodeError as repair_error:
        raise ai_service_error(
            f"AI返回的JSON格式不正确，自动修复后仍无法解析：{repair_error.msg}，line {repair_error.lineno} column {repair_error.colno}"
        ) from repair_error


class AiTaskService:
    @staticmethod
    def update_progress(
            task: AiAgentTask,
            percent: int,
            stage: str,
            detail: str = "",
            extra: dict | None = None,
    ):
        percent = max(0, min(100, int(percent)))
        output_data = dict(task.output_data or {})
        output_data["progress"] = mask_sensitive(
            {
                "percent": percent,
                "stage": stage,
                "detail": detail,
                "updated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                **(extra or {}),
            }
        )
        AiAgentTask.objects.filter(
            id=task.id,
            status__in=[
                AiAgentTaskStatusEnum.PENDING.value,
                AiAgentTaskStatusEnum.CLAIMED.value,
                AiAgentTaskStatusEnum.RUNNING.value,
                AiAgentTaskStatusEnum.WAITING_MODEL.value,
            ],
        ).update(output_data=output_data, update_time=timezone.now())
        task.output_data = output_data

    @staticmethod
    def create_task(
            task_type: int,
            title: str,
            input_data: dict,
            user_id: int | None = None,
            skill: AiSkill | None = None,
            definition=None,
    ) -> AiAgentTask:
        from src.apps.ai.services.harness.skill_version import SkillVersionService

        config = AiService.load_config()
        now_text = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_input = mask_sensitive(input_data)
        skill_version = SkillVersionService.resolve(skill, user_id)
        task = AiAgentTask.objects.create(
            task_no=f"AI{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8]}",
            task_type=task_type,
            title=title,
            status=AiAgentTaskStatusEnum.PENDING.value,
            input_data=safe_input,
            input_snapshot=safe_input,
            output_data={
                "progress": {
                    "percent": 0,
                    "stage": "任务已创建",
                    "detail": "正在准备执行",
                    "updated_at": now_text,
                }
            },
            create_user_id=user_id,
            skill=skill,
            model_name=config.model,
            model_snapshot={"model": config.model, "base_url": config.base_url},
            agent_key=getattr(definition, "agent_key", None),
            agent_version=getattr(definition, "version", None),
            context_hash=input_data.get("context_hash"),
            skill_version=skill_version,
            mcp_snapshot={
                "server_ids": input_data.get("mcp_server_ids") or [],
                "server_names": input_data.get("mcp_server_names") or [],
                "server_prompts": input_data.get("mcp_server_prompts") or {},
            },
        )
        return task

    @staticmethod
    def finish_task(task: AiAgentTask, output_data: dict, status: str = AiAgentTaskStatusEnum.SUCCESS.value):
        existing_output = dict(task.output_data or {})
        progress = dict(existing_output.get("progress") or {})
        progress.update({"percent": 100, "stage": "已完成", "detail": progress.get("detail") or "任务已完成"})
        output_data = {**existing_output, **mask_sensitive(output_data), "progress": progress}
        task.status = status
        task.output_data = output_data
        task.result_summary = mask_sensitive(output_data)
        task.error_message = None
        task.save(update_fields=["status", "output_data", "result_summary", "error_message", "update_time"])
        return task

    @staticmethod
    def fail_task(task: AiAgentTask, message: str, output_data: dict | None = None):
        existing_output = dict(task.output_data or {})
        progress = dict(existing_output.get("progress") or {})
        cancelled = bool(task.cancel_requested or task.status == AiAgentTaskStatusEnum.CANCELLED.value)
        progress.update(
            {
                "percent": progress.get("percent") if progress.get("percent") is not None else 100,
                "stage": "已取消" if cancelled else "已失败",
                "detail": message[:300],
            }
        )
        task.status = AiAgentTaskStatusEnum.CANCELLED.value if cancelled else AiAgentTaskStatusEnum.FAIL.value
        task.error_message = message[:1000]
        task.output_data = {**existing_output, **mask_sensitive(output_data or {}), "progress": progress}
        task.save(update_fields=["status", "error_message", "output_data", "update_time"])
        return task

    @classmethod
    def reconcile_interrupted_task(cls, task: AiAgentTask) -> AiAgentTask:
        if task.status == AiAgentTaskStatusEnum.PENDING.value:
            return task
        if task.status not in [
            AiAgentTaskStatusEnum.CLAIMED.value,
            AiAgentTaskStatusEnum.RUNNING.value,
            AiAgentTaskStatusEnum.WAITING_MODEL.value,
        ]:
            return task
        if task.lease_expires_at and task.lease_expires_at >= timezone.now():
            return task
        task.status = AiAgentTaskStatusEnum.PENDING.value
        task.worker_id = None
        task.lease_expires_at = None
        task.save(
            update_fields=["status", "worker_id", "lease_expires_at", "update_time"]
        )
        return task


class SkillService:
    @staticmethod
    def published_skill(scenario_type: str | None = None, skill_id: int | None = None) -> AiSkill | None:
        queryset = AiSkill.objects.filter(status=AiSkillStatusEnum.PUBLISHED.value)
        if skill_id:
            return queryset.filter(id=skill_id).first()
        return queryset.order_by("-id").first()

    @staticmethod
    def publish(skill: AiSkill) -> AiSkill:
        if skill.status == AiSkillStatusEnum.PUBLISHED.value:
            return skill
        skill.status = AiSkillStatusEnum.PUBLISHED.value
        skill.save(update_fields=["status", "update_time"])
        return skill


class McpService:
    BUILTIN_MCP_NAME = "MangoTestingPlatform"
    BUILTIN_MCP_DESCRIPTION = "芒果测试平台内置 MCP 服务，提供平台工具与版本化 Skill"

    BUILTIN_TOOL_GROUPS = [
        {
            "key": "project_context",
            "title": "项目上下文",
            "description": "项目、用户、测试环境上下文",
            "tools": [
                "get_current_user_context",
                "list_project_products",
                "list_product_modules",
                "list_case_owners",
                "list_test_environments",
                "ensure_user_test_environment",
            ],
        },
        {
            "key": "api_automation",
            "title": "API自动化",
            "description": "API 接口、用例、场景、执行和结果分析",
            "tools": [
                "list_api_headers",
                "preview_create_api_header_impact",
                "create_api_header",
                "update_api_header",
                "list_api_public_variables",
                "create_api_public_variable",
                "update_api_public_variable",
                "set_api_public_variable_status",
                "search_api_infos",
                "get_api_info_detail",
                "create_api_info",
                "create_api_info_from_curl",
                "update_api_info",
                "create_grpc_service",
                "update_grpc_service",
                "list_grpc_services",
                "get_grpc_service_detail",
                "sync_grpc_methods",
                "list_grpc_methods",
                "import_grpc_method_to_api_info",
                "import_mcp_tool_to_api_info",
                "run_api_info",
                "create_api_info_revision_from_current",
                "publish_api_info_revision",
                "create_api_case",
                "search_api_cases",
                "get_api_case_detail_full",
                "update_api_case",
                "preview_delete_api_case_impact",
                "delete_api_case",
                "add_api_case_step",
                "list_api_case_steps",
                "sort_api_case_steps",
                "refresh_api_case_step_from_api_info",
                "list_api_case_scenarios",
                "create_api_case_scenario",
                "update_api_case_scenario",
                "preview_delete_api_case_scenario_impact",
                "delete_api_case_scenario",
                "get_api_assertion_schema",
                "get_api_assertion_methods",
                "generate_api_case_scenario_assertions",
                "auto_generate_api_case_scenario_schema",
                "generate_api_case_scenario_extractors",
                "create_complete_api_case",
                "run_api_case",
                "get_api_case_run_result",
                "analyze_api_case_failure",
                "create_api_case_revision_from_current",
                "update_api_case_publication_status",
                "get_api_case_schema",
            ],
        },
        {
            "key": "data_factory",
            "title": "数据工厂",
            "description": "数据实体、字段、模板、预览、绑定和清理",
            "tools": [
                "get_data_factory_schema",
                "list_data_factory_datasource_aliases",
                "list_data_factory_datasource_bindings",
                "list_data_factory_database_tables",
                "get_data_factory_table_schema",
                "list_data_factory_entities",
                "get_data_factory_entity_detail",
                "create_data_factory_entity",
                "batch_generate_data_factory_entities",
                "list_data_factory_fields",
                "batch_save_data_factory_fields",
                "preview_data_factory_field_values",
                "list_data_factory_templates",
                "get_data_factory_template_detail",
                "create_data_factory_template",
                "update_data_factory_template",
                "set_data_factory_template_status",
                "preview_data_factory_template",
                "preview_run_data_factory_template_impact",
                "execute_data_factory_template",
                "list_data_factory_case_configs",
                "update_data_factory_case_config",
                "sort_data_factory_case_configs",
                "preview_data_factory_case_config",
                "bind_data_factory_to_case_source",
                "list_data_factory_executions",
                "get_data_factory_execution_detail",
                "preview_cleanup_data_factory_execution_impact",
                "cleanup_data_factory_execution",
            ],
        },
        {
            "key": "ui_automation",
            "title": "UI自动化",
            "description": "UI 自动化查询与手动绑定辅助",
            "tools": [
                "search_ui_cases",
                "get_ui_case_detail",
            ],
        },
        {
            "key": "functional_test",
            "title": "功能测试",
            "description": "功能测试需求、用例、上下文资料、自动化绑定、统计和模块导航",
            "tools": [
                "list_functional_test_suites",
                "get_functional_test_suite_detail",
                "create_functional_test_suite",
                "update_functional_test_suite",
                "delete_functional_test_suite",
                "list_functional_test_cases",
                "get_functional_test_case_detail",
                "create_functional_test_case",
                "update_functional_test_case",
                "delete_functional_test_case",
                "batch_delete_functional_test_cases",
                "list_functional_test_context_resources",
                "get_functional_test_context_resource_detail",
                "create_functional_test_context_resource",
                "update_functional_test_context_resource",
                "delete_functional_test_context_resource",
                "list_functional_test_automation_bindings",
                "bind_functional_test_automation_case",
                "list_functional_test_case_modules",
                "get_functional_test_suite_stats",
            ],
        },
        {
            "key": "scheduled_task",
            "title": "定时任务",
            "description": "定时任务和任务明细绑定",
            "tools": [
                "preview_bind_cases_to_scheduled_task_impact",
                "bind_cases_to_scheduled_task",
                "preview_unbind_cases_from_scheduled_task_impact",
                "unbind_cases_from_scheduled_task",
            ],
        },
        {
            "key": "ai_platform",
            "title": "AI平台",
            "description": "AI、Skill、MCP 服务和任务记录查询",
            "tools": [
                "list_ai_skills",
                "get_ai_skill_detail",
                "list_ai_mcp_servers",
                "create_ai_mcp_server",
                "update_ai_mcp_server",
                "sync_ai_mcp_server_tools",
                "get_ai_mcp_server_detail",
                "list_ai_mcp_tools",
                "list_ai_agent_tasks",
                "get_ai_agent_task_detail",
                "list_ai_agent_tool_calls",
                "list_ai_assistant_sessions",
                "list_ai_assistant_messages",
            ],
        },
        {
            "key": "system_assets",
            "title": "系统资源",
            "description": "系统变量、文件和认证配置",
            "tools": [
                "list_system_variables",
                "create_system_variable",
                "update_system_variable",
                "set_system_variable_status",
                "upload_system_file_from_url",
                "list_system_files",
                "list_api_auth_configs",
                "create_api_auth_config",
                "update_api_auth_config",
                "refresh_api_auth_config",
                "preview_clear_api_auth_config_cache_impact",
                "clear_api_auth_config_cache",
                "preview_delete_api_auth_config_impact",
                "delete_api_auth_config",
                "list_api_auth_time_tasks",
            ],
        },
    ]
    WRITE_PREFIXES = (
        "create_",
        "add_",
        "copy_",
        "upload_",
        "bind_",
        "unbind_",
        "batch_generate_",
        "execute_",
        "debug_run_",
        "update_",
        "set_",
        "sort_",
        "refresh_",
        "auto_generate_",
        "delete_",
        "cleanup_",
        "clear_",
    )
    ONLINE_CACHE_SECONDS = 120

    @classmethod
    def tool_category(cls, tool_name: str) -> dict:
        for group in cls.BUILTIN_TOOL_GROUPS:
            if tool_name in group["tools"]:
                return {
                    "key": group["key"],
                    "title": group["title"],
                    "description": group["description"],
                }
        if tool_name.startswith(("get_mcp_", "list_ai_", "get_ai_")):
            return {"key": "ai_platform", "title": "AI平台", "description": "AI、Skill、MCP 服务和任务记录查询"}
        if "data_factory" in tool_name:
            return {"key": "data_factory", "title": "数据工厂", "description": "数据实体、字段、模板、预览、绑定和清理"}
        if "grpc" in tool_name or tool_name.startswith(
                ("search_api_", "get_api_", "create_api_", "update_api_", "delete_api_", "run_api_", "analyze_api_",
                 "add_api_", "sort_api_", "refresh_api_", "copy_api_", "auto_generate_api_", "generate_api_")):
            return {"key": "api_automation", "title": "API自动化", "description": "API 接口、用例、场景、执行和结果分析"}
        if "_ui_" in tool_name or tool_name.startswith(
                ("search_ui_", "get_ui_", "create_ui_", "update_ui_", "delete_ui_")):
            return {"key": "ui_automation", "title": "UI自动化", "description": "UI 自动化查询与手动绑定辅助"}
        if "functional_test" in tool_name:
            return {"key": "functional_test", "title": "功能测试",
                    "description": "功能测试需求、用例、上下文资料、自动化绑定、统计和模块导航"}
        if "scheduled_task" in tool_name or "time_task" in tool_name:
            return {"key": "scheduled_task", "title": "定时任务", "description": "定时任务和任务明细绑定"}
        return {"key": "other", "title": "其他", "description": "未归类工具"}

    @classmethod
    def assistant_tool_categories(cls, content: str) -> set[str]:
        text = (content or "").lower()
        categories = {"project_context"}
        if any(keyword in text for keyword in
               ("数据工厂", "造数", "数据库", "sql", "表结构", "实体", "字段", "datasource", "factory")):
            categories.add("data_factory")
        if any(keyword in text for keyword in
               ("api", "接口", "case", "用例", "请求", "响应", "断言", "提取", "header", "curl")):
            categories.add("api_automation")
        if any(keyword in text for keyword in ("ui", "页面", "元素", "定位", "前端自动化")):
            categories.add("ui_automation")
        if any(keyword in text for keyword in
               ("功能测试", "需求列表", "需求文档", "原始case", "手工测试", "手工用例", "测试用例", "用例同步")):
            categories.add("functional_test")
        if any(keyword in text for keyword in ("定时任务", "任务明细", "绑定任务", "scheduled")):
            categories.add("scheduled_task")
        if any(keyword in text for keyword in ("mcp", "skill", "技能", "ai任务", "执行记录", "助手", "工具")):
            categories.add("ai_platform")
        if any(keyword in text for keyword in ("系统变量", "公共变量", "文件", "上传", "token", "鉴权", "认证")):
            categories.add("system_assets")
        return categories

    @classmethod
    def infer_risk(cls, tool_name: str) -> tuple[str, bool, bool]:
        if tool_name.startswith(("preview_", "analyze_", "generate_")):
            return AiMcpToolRiskLevelEnum.PREVIEW.value, False, False
        if tool_name.startswith(("run_", "execute_", "debug_run_")):
            return AiMcpToolRiskLevelEnum.EXECUTE.value, True, True
        if tool_name.startswith(("delete_", "cleanup_", "clear_", "unbind_")):
            return AiMcpToolRiskLevelEnum.DELETE.value, True, True
        if tool_name.startswith(cls.WRITE_PREFIXES):
            return AiMcpToolRiskLevelEnum.WRITE.value, True, True
        return AiMcpToolRiskLevelEnum.READ.value, False, False

    @staticmethod
    def request_user_id(request_or_user) -> int | None:
        user = getattr(request_or_user, "user", request_or_user)
        if isinstance(user, dict):
            return user.get("id")
        return getattr(user, "id", None)

    @classmethod
    def ensure_builtin_server(cls, request) -> AiMcpServer:
        server_url = request.build_absolute_uri("/mcp")
        auth_config = {
            "builtin": True,
            "builtin_local": True,
            "use_current_user_api_key": True,
        }
        server = AiMcpServer.objects.filter(auth_config__builtin_local=True).first()
        if not server:
            server = AiMcpServer.objects.filter(server_url=server_url, name=cls.BUILTIN_MCP_NAME).first()
        if server:
            changed_fields = []
            if server.server_url != server_url:
                server.server_url = server_url
                changed_fields.append("server_url")
            if server.transport_type != AiMcpTransportTypeEnum.STREAMABLE_HTTP.value:
                server.transport_type = AiMcpTransportTypeEnum.STREAMABLE_HTTP.value
                changed_fields.append("transport_type")
            if server.auth_type != AiMcpAuthTypeEnum.BEARER.value:
                server.auth_type = AiMcpAuthTypeEnum.BEARER.value
                changed_fields.append("auth_type")
            merged_config = {**(server.auth_config or {}), **auth_config}
            if server.auth_config != merged_config:
                server.auth_config = merged_config
                changed_fields.append("auth_config")
            if not server.prompt:
                server.prompt = get_prompt("ai.mcp_service").system
                changed_fields.append("prompt")
            if changed_fields:
                server.save(update_fields=[*changed_fields, "update_time"])
            return server
        return AiMcpServer.objects.create(
            name=cls.BUILTIN_MCP_NAME,
            server_url=server_url,
            transport_type=AiMcpTransportTypeEnum.STREAMABLE_HTTP.value,
            auth_type=AiMcpAuthTypeEnum.BEARER.value,
            auth_config=auth_config,
            description=cls.BUILTIN_MCP_DESCRIPTION,
            prompt=get_prompt("ai.mcp_service").system,
            status=AiMcpStatusEnum.ENABLED.value,
        )

    @classmethod
    def set_builtin(cls, server: AiMcpServer, is_builtin: bool) -> AiMcpServer:
        config = dict(server.auth_config or {})
        config.pop("builtin_manual", None)
        if is_builtin:
            cls.clear_builtin_flags(exclude_id=server.id)
            config["builtin"] = True
        else:
            config.pop("builtin", None)
        server.auth_config = config
        server.save(update_fields=["auth_config", "update_time"])
        cls.ensure_one_builtin()
        return server

    @classmethod
    def clear_builtin_flags(cls, exclude_id: int | None = None):
        queryset = AiMcpServer.objects.filter(auth_config__builtin=True)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        for item in queryset:
            config = dict(item.auth_config or {})
            config.pop("builtin", None)
            config.pop("builtin_manual", None)
            item.auth_config = config
            item.save(update_fields=["auth_config", "update_time"])

    @classmethod
    def ensure_one_builtin(cls):
        builtin_servers = list(AiMcpServer.objects.filter(auth_config__builtin=True).order_by("id"))
        if len(builtin_servers) > 1:
            keep = builtin_servers[0]
            cls.clear_builtin_flags(exclude_id=keep.id)

    @classmethod
    def builtin_candidates(cls, request):
        cls.ensure_builtin_server(request)
        cls.ensure_one_builtin()
        candidates = list(
            AiMcpServer.objects.filter(
                status=AiMcpStatusEnum.ENABLED.value,
                auth_config__builtin=True,
            )
        )
        return sorted(candidates, key=lambda item: 1 if (item.auth_config or {}).get("builtin_local") else 0)

    @classmethod
    def select_online_builtin_server(cls, request) -> tuple[AiMcpServer | None, list[dict]]:
        user_id = cls.request_user_id(request)
        candidates = cls.builtin_candidates(request)
        statuses = []
        selected = None
        for server in candidates:
            result = cls.test_server(server, user_id)
            row = {
                "server_id": server.id,
                "server_name": server.name,
                "server_url": server.server_url,
                "is_connected": bool(result.get("ok")),
                "last_error": result.get("error") or server.last_error,
                "is_local": bool((server.auth_config or {}).get("builtin_local")),
                "is_manual": bool((server.auth_config or {}).get("builtin_manual")),
            }
            statuses.append(row)
            if row["is_connected"] and not selected:
                selected = server
        return selected, statuses

    @classmethod
    def mcp_candidates(cls, request):
        builtin = cls.builtin_candidates(request)
        builtin_ids = {item.id for item in builtin}
        external = list(
            AiMcpServer.objects.filter(status=AiMcpStatusEnum.ENABLED.value).exclude(id__in=builtin_ids)
        )
        return [*builtin, *external]

    @classmethod
    def select_online_server(cls, request, preferred_server_id: int | None = None) -> tuple[
        AiMcpServer | None, list[dict]]:
        user_id = cls.request_user_id(request)
        statuses = []
        selected = None
        candidates = cls.mcp_candidates(request)
        preferred_id = int(preferred_server_id) if preferred_server_id else None
        if preferred_server_id:
            preferred = next((item for item in candidates if item.id == preferred_id), None)
            if preferred:
                candidates = [preferred, *[item for item in candidates if item.id != preferred.id]]
        for server in candidates:
            config = server.auth_config or {}
            cached_connected = (
                    preferred_id == server.id
                    and server.last_test_time
                    and not server.last_error
                    and timezone.now() - server.last_test_time <= timedelta(seconds=cls.ONLINE_CACHE_SECONDS)
            )
            result = {"ok": True} if cached_connected else cls.test_server(server, user_id)
            row = {
                "server_id": server.id,
                "server_name": server.name,
                "server_url": server.server_url,
                "is_connected": bool(result.get("ok")),
                "last_error": result.get("error") or server.last_error,
                "from_cache": cached_connected,
                "is_builtin": bool(config.get("builtin")),
                "is_local": bool(config.get("builtin_local")),
                "is_manual": bool(config.get("builtin_manual")),
            }
            statuses.append(row)
            if row["is_connected"] and not selected:
                selected = server
        return selected, statuses

    @staticmethod
    def test_server(server: AiMcpServer, user_id: int | None = None) -> dict:
        if server.status != AiMcpStatusEnum.ENABLED.value:
            return {
                "ok": False,
                "skipped": True,
                "error": "MCP服务已停用，未执行连接测试",
            }
        server.last_test_time = timezone.now()
        try:
            capabilities = ExternalMcpClient.list_capabilities(server, user_id)
            server.last_error = None
            server.save(update_fields=["last_test_time", "last_error", "update_time"])
            return {
                "ok": True,
                "tools": len(capabilities.get("tools") or []),
                "resources": len(capabilities.get("resources") or []),
                "prompts": len(capabilities.get("prompts") or []),
                "initialize": capabilities.get("initialize") or {},
            }
        except Exception as exc:
            error_message = ExternalMcpClient.format_exception(exc)
            server.last_error = error_message[:1000]
            server.save(update_fields=["last_test_time", "last_error", "update_time"])
            return {"ok": False, "error": error_message}

    @classmethod
    def refresh_statuses(cls, servers, user_id: int | None = None) -> list[dict]:
        results = []
        for server in servers:
            result = cls.test_server(server, user_id)
            results.append({"id": server.id, **result})
        return results

    @classmethod
    def sync_tools(cls, server: AiMcpServer, user_id: int | None = None, test_env: int | None = None) -> dict:
        if server.status != AiMcpStatusEnum.ENABLED.value:
            return {
                "count": 0,
                "skipped": True,
                "error": "MCP服务已停用，未执行工具同步",
            }
        capabilities = cls.list_capabilities_for_sync(server, user_id, test_env)
        count = 0
        remote_keys = set()
        for item in capabilities.get("tools") or []:
            tool_name = item.get("name")
            if not tool_name:
                continue
            remote_keys.add(("tool", tool_name))
            risk_level, write_operation, require_confirm = cls.infer_risk(tool_name)
            tool, _created = AiMcpTool.objects.update_or_create(
                server=server,
                name=tool_name,
                tool_type="tool",
                defaults={
                    "type": server.type,
                    "title": item.get("title") or tool_name,
                    "description": item.get("description") or "",
                    "input_schema": item.get("inputSchema") or {},
                    "output_schema": item.get("outputSchema") or {},
                    "risk_level": risk_level,
                    "write_operation": write_operation,
                    "require_confirm": require_confirm,
                    "enabled": True,
                },
            )
            cls.record_tool_snapshot(
                tool,
                test_env=test_env,
                protocol_version=(capabilities.get("initialize") or {}).get("protocolVersion"),
            )
            count += 1
        for tool_type, rows in (("resource", capabilities.get("resources") or []),
                                ("prompt", capabilities.get("prompts") or [])):
            for item in rows:
                tool_name = item.get("name") or item.get("uri")
                if not tool_name:
                    continue
                remote_keys.add((tool_type, tool_name))
                risk_level, write_operation, require_confirm = cls.infer_risk(tool_name)
                tool, _created = AiMcpTool.objects.update_or_create(
                    server=server,
                    name=tool_name,
                    tool_type=tool_type,
                    defaults={
                        "type": server.type,
                        "title": item.get("title") or item.get("name") or tool_name,
                        "description": item.get("description") or "",
                        "input_schema": item,
                        "output_schema": {},
                        "risk_level": risk_level,
                        "write_operation": write_operation,
                        "require_confirm": require_confirm,
                        "enabled": True,
                    },
                )
                cls.record_tool_snapshot(
                    tool,
                    test_env=test_env,
                    protocol_version=(capabilities.get("initialize") or {}).get("protocolVersion"),
                )
                count += 1
        if test_env in (None, "", "null", "undefined"):
            existing_tools = AiMcpTool.objects.filter(server=server)
            for existing in existing_tools:
                if (existing.tool_type, existing.name) not in remote_keys and existing.enabled:
                    existing.enabled = False
                    existing.save(update_fields=["enabled", "update_time"])
                    cls.disable_imported_api_info(existing)
        server.last_sync_time = timezone.now()
        server.last_error = None
        server.save(update_fields=["last_sync_time", "last_error", "update_time"])
        return {
            "synced_count": count,
            "tools": len(capabilities.get("tools") or []),
            "resources": len(capabilities.get("resources") or []),
            "prompts": len(capabilities.get("prompts") or []),
        }

    @classmethod
    def list_capabilities_for_sync(cls, server: AiMcpServer, user_id: int | None = None,
                                   test_env: int | None = None) -> dict:
        if server.type not in {AiMcpUseTypeEnum.API_AUTOMATION.value, AiMcpUseTypeEnum.COMMON.value} or test_env in (
                None, "", "null", "undefined"):
            return ExternalMcpClient.list_capabilities(server, user_id)
        if not server.project_product_id:
            return ExternalMcpClient.list_capabilities(server, user_id)

        from src.apps.auto_api.services.base.api_base_test_setup import APIBaseTestSetup

        setup = APIBaseTestSetup()
        setup.init_test_object(server.project_product_id, int(test_env))
        setup.init_public(server.project_product_id, int(test_env))
        headers = setup.init_headers(server.project_product_id) or {}
        clean_headers = {
            key: setup.test_data.replace(value)
            for key, value in headers.items()
            if str(key).lower() not in {"content-type", "accept", "mcp-protocol-version", "mcp-session-id"}
        }
        server_url = server.server_url
        parsed = urlparse(server_url)
        if not parsed.scheme or not parsed.netloc:
            from src.apps.test_center.services.test_target import TestTargetService
            server_url = urljoin(TestTargetService.resolve(setup.test_object, setup.test_data), server_url)
        return ExternalMcpClient.list_capabilities_runtime(
            server_url=server_url,
            transport_type=server.transport_type,
            headers=clean_headers,
            timeout_seconds=60,
        )

    @classmethod
    def sync_builtin_tools(cls, server: AiMcpServer, user_id: int | None = None) -> dict:
        return cls.sync_tools(server, user_id)

    @staticmethod
    def disable_imported_api_info(tool: AiMcpTool):
        try:
            ApiInfoMcpImportService.disable_for_tool(tool.id)
        except Exception as error:
            log.system.error(f'MCP Tool下线同步ApiInfo状态失败，tool_id={tool.id}，错误：{error}')

    @staticmethod
    def record_tool_snapshot(tool: AiMcpTool, test_env: int | None = None, protocol_version: str | None = None):
        if test_env in ("", "null", "undefined"):
            test_env = None
        if test_env is not None:
            test_env = int(test_env)
        schema_hash = McpService.schema_hash(tool.input_schema, tool.output_schema)
        latest = (
            AiMcpToolSnapshot.objects
            .filter(tool=tool, test_env=test_env)
            .order_by('-id')
            .first()
        )
        if latest and latest.schema_hash == schema_hash and latest.is_available:
            return latest
        return AiMcpToolSnapshot.objects.create(
            server=tool.server,
            tool=tool,
            test_env=test_env,
            protocol_version=protocol_version,
            input_schema=tool.input_schema or {},
            output_schema=tool.output_schema or {},
            schema_hash=schema_hash,
            is_available=tool.enabled,
            sync_error=None,
        )

    @staticmethod
    def schema_hash(input_schema: dict | None, output_schema: dict | None) -> str:
        payload = json.dumps(
            {"input_schema": input_schema or {}, "output_schema": output_schema or {}},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        import hashlib
        return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"

    @staticmethod
    def call_tool(server: AiMcpServer, tool_name: str, arguments: dict | None = None,
                  user_id: int | None = None) -> dict:
        return ExternalMcpClient.call_tool(server, tool_name, arguments or {}, user_id)

    @staticmethod
    def log_tool_call(
            task: AiAgentTask,
            tool_name: str,
            arguments: dict,
            result: dict,
            server: AiMcpServer | None = None,
            *,
            task_item_id: int | None = None,
            stage_key: str | None = None,
            duration_ms: int | None = None,
            request_hash: str | None = None,
            result_hash: str | None = None,
            idempotency_key: str | None = None,
            mcp_tool_schema_hash: str | None = None,
            external_asset_ids: dict | None = None,
    ):
        status = AiAgentToolCallStatusEnum.SUCCESS.value if McpService.is_tool_call_success(
            result) else AiAgentToolCallStatusEnum.FAIL.value
        return AiAgentToolCall.objects.create(
            task=task,
            server=server,
            tool_name=tool_name,
            arguments=mask_sensitive(arguments),
            result=mask_sensitive(result),
            status=status,
            risk_level=McpService.infer_risk(tool_name)[0],
            confirm_required=McpService.infer_risk(tool_name)[2],
            error_message="" if status == AiAgentToolCallStatusEnum.SUCCESS.value else McpService.extract_tool_call_error(
                result),
            start_time=timezone.now(),
            end_time=timezone.now(),
            task_item_id=task_item_id,
            stage_key=stage_key,
            duration_ms=duration_ms,
            request_hash=request_hash,
            result_hash=result_hash,
            idempotency_key=idempotency_key,
            mcp_tool_schema_hash=mcp_tool_schema_hash,
            external_asset_ids=external_asset_ids or {},
        )

    @staticmethod
    def is_tool_call_success(result: dict | None) -> bool:
        if not isinstance(result, dict):
            return False
        if result.get("isError") is True:
            return False
        if result.get("success") is False:
            return False
        content = result.get("content")
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict) or not isinstance(item.get("text"), str):
                    continue
                try:
                    nested = json.loads(item["text"])
                except (TypeError, ValueError, json.JSONDecodeError):
                    continue
                if isinstance(nested, dict) and (
                        nested.get("success") is False or nested.get("isError") is True
                ):
                    return False
        return True

    @staticmethod
    def extract_tool_call_error(result: dict | None) -> str:
        if not isinstance(result, dict):
            return "MCP工具调用失败"
        message = result.get("message") or result.get("error") or result.get("error_message")
        if message:
            return str(message)[:1000]
        content = result.get("content")
        if isinstance(content, list):
            texts = [item.get("text") for item in content if isinstance(item, dict) and item.get("text")]
            if texts:
                return "\n".join(texts)[:1000]
        return "MCP工具调用失败"
