# -*- coding: utf-8 -*-
import json
import re
import time
import uuid
from datetime import datetime, timedelta
from threading import Lock, Thread
from typing import Any

from django.db import close_old_connections
from django.utils import timezone

from src.apps.ai.models import AiAgentTask, AiAgentToolCall, AiMcpServer, AiMcpTool, AiSkill
from src.apps.ai.service.mcp_client import ExternalMcpClient
from src.apps.system.service.ai.client import AiService
from src.common.enums.ai_enum import (
    AiAgentTaskStatusEnum,
    AiAgentTaskTypeEnum,
    AiAgentToolCallStatusEnum,
    AiMcpAuthTypeEnum,
    AiMcpStatusEnum,
    AiMcpToolRiskLevelEnum,
    AiMcpTransportTypeEnum,
    AiSkillStatusEnum,
)


SENSITIVE_KEYS = {"api_key", "authorization", "password", "cookie", "token", "secret"}
PROCESS_START_TIME = timezone.now()


def mask_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if str(key).lower() in SENSITIVE_KEYS else mask_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [mask_sensitive(item) for item in value]
    return value


def extract_ai_json(response: dict) -> dict:
    choices = response.get("choices") or []
    if not choices:
        return {}
    message = choices[0].get("message") or {}
    content = message.get("content") or "{}"
    if isinstance(content, dict):
        return content
    return parse_ai_json_content(str(content))


def parse_ai_json_content(content: str, *, allow_ai_repair: bool = True) -> dict:
    json_content = extract_json_text(content)
    try:
        return json.loads(json_content)
    except json.JSONDecodeError as exc:
        if not allow_ai_repair:
            raise
        return repair_ai_json_content(json_content, exc)


def extract_json_text(content: str) -> str:
    text = (content or "{}").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return text


def repair_ai_json_content(content: str, error: json.JSONDecodeError) -> dict:
    repair_messages = [
        {
            "role": "system",
            "content": (
                "你是严格的 JSON 修复器。只修复 JSON 语法错误，不新增业务内容，不删除已有字段，不解释原因。"
                "输出必须是一个可被 json.loads 解析的 JSON object。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"下面 JSON 解析失败：{error.msg}，line {error.lineno} column {error.colno}。"
                "请修复为合法 JSON object，并保持原有结构和字段含义。\n\n"
                f"{content[:120000]}"
            ),
        },
    ]
    repaired_response = AiService.json_chat(repair_messages, max_tokens=16000)
    choices = repaired_response.get("choices") or []
    if not choices:
        raise ValueError(f"AI返回的JSON格式不正确，且自动修复失败：{error.msg}")
    repaired_content = choices[0].get("message", {}).get("content") or "{}"
    if isinstance(repaired_content, dict):
        return repaired_content
    try:
        return parse_ai_json_content(str(repaired_content), allow_ai_repair=False)
    except json.JSONDecodeError as repair_error:
        raise ValueError(
            f"AI返回的JSON格式不正确，自动修复后仍无法解析：{repair_error.msg}，line {repair_error.lineno} column {repair_error.colno}"
        ) from repair_error


class AiTaskService:
    RUNNING_TASK_IDS: set[int] = set()
    HEARTBEAT_TASK_IDS: set[int] = set()
    RUNNING_TASK_LOCK = Lock()
    HEARTBEAT_INTERVAL_SECONDS = 30
    STALE_BUFFER_SECONDS = 60
    MIN_STALE_SECONDS = 900

    @classmethod
    def mark_running(cls, task: AiAgentTask):
        start_heartbeat = False
        with cls.RUNNING_TASK_LOCK:
            cls.RUNNING_TASK_IDS.add(task.id)
            if task.id not in cls.HEARTBEAT_TASK_IDS:
                cls.HEARTBEAT_TASK_IDS.add(task.id)
                start_heartbeat = True
        if start_heartbeat:
            Thread(target=cls._heartbeat_task, args=(task.id,), daemon=True).start()

    @classmethod
    def clear_running(cls, task: AiAgentTask):
        with cls.RUNNING_TASK_LOCK:
            cls.RUNNING_TASK_IDS.discard(task.id)

    @classmethod
    def is_running_in_current_process(cls, task: AiAgentTask) -> bool:
        with cls.RUNNING_TASK_LOCK:
            return task.id in cls.RUNNING_TASK_IDS

    @classmethod
    def _heartbeat_task(cls, task_id: int):
        try:
            while True:
                time.sleep(cls.HEARTBEAT_INTERVAL_SECONDS)
                with cls.RUNNING_TASK_LOCK:
                    if task_id not in cls.RUNNING_TASK_IDS:
                        break
                close_old_connections()
                updated = AiAgentTask.objects.filter(
                    id=task_id,
                    status__in=[AiAgentTaskStatusEnum.PENDING.value, AiAgentTaskStatusEnum.RUNNING.value],
                ).update(update_time=timezone.now())
                if not updated:
                    break
        finally:
            with cls.RUNNING_TASK_LOCK:
                cls.RUNNING_TASK_IDS.discard(task_id)
                cls.HEARTBEAT_TASK_IDS.discard(task_id)
            close_old_connections()

    @classmethod
    def stale_seconds(cls) -> int:
        try:
            timeout = int(AiService.load_config().timeout or 60)
        except Exception:
            timeout = 60
        return max(cls.MIN_STALE_SECONDS, timeout * 3)

    @staticmethod
    def touch_task(task: AiAgentTask):
        AiAgentTask.objects.filter(
            id=task.id,
            status__in=[AiAgentTaskStatusEnum.PENDING.value, AiAgentTaskStatusEnum.RUNNING.value],
        ).update(update_time=timezone.now())

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
            status__in=[AiAgentTaskStatusEnum.PENDING.value, AiAgentTaskStatusEnum.RUNNING.value],
        ).update(output_data=output_data, update_time=timezone.now())
        task.output_data = output_data

    @staticmethod
    def create_task(task_type: int, title: str, input_data: dict, user_id: int | None = None, skill: AiSkill | None = None) -> AiAgentTask:
        config = AiService.load_config()
        now_text = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        task = AiAgentTask.objects.create(
            task_no=f"AI{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8]}",
            task_type=task_type,
            title=title,
            status=AiAgentTaskStatusEnum.RUNNING.value,
            input_data=mask_sensitive(input_data),
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
        )
        AiTaskService.mark_running(task)
        return task

    @staticmethod
    def finish_task(task: AiAgentTask, output_data: dict, status: str = AiAgentTaskStatusEnum.SUCCESS.value):
        existing_output = dict(task.output_data or {})
        progress = dict(existing_output.get("progress") or {})
        progress.update({"percent": 100, "stage": "已完成", "detail": progress.get("detail") or "任务已完成"})
        output_data = {**existing_output, **mask_sensitive(output_data), "progress": progress}
        task.status = status
        task.output_data = output_data
        task.error_message = None
        task.save(update_fields=["status", "output_data", "error_message", "update_time"])
        AiTaskService.clear_running(task)
        return task

    @staticmethod
    def fail_task(task: AiAgentTask, message: str, output_data: dict | None = None):
        existing_output = dict(task.output_data or {})
        progress = dict(existing_output.get("progress") or {})
        progress.update(
            {
                "percent": progress.get("percent") or 100,
                "stage": "已失败",
                "detail": message[:300],
            }
        )
        task.status = AiAgentTaskStatusEnum.FAIL.value
        task.error_message = message[:1000]
        task.output_data = {**existing_output, **mask_sensitive(output_data or {}), "progress": progress}
        task.save(update_fields=["status", "error_message", "output_data", "update_time"])
        AiTaskService.clear_running(task)
        return task

    @classmethod
    def reconcile_interrupted_task(cls, task: AiAgentTask) -> AiAgentTask:
        if task.status not in [AiAgentTaskStatusEnum.PENDING.value, AiAgentTaskStatusEnum.RUNNING.value]:
            return task
        if cls.is_running_in_current_process(task):
            return task
        update_time = task.update_time or task.create_time
        if update_time and update_time < PROCESS_START_TIME:
            return cls.fail_task(
                task,
                "任务已中断：后端服务已重启，原任务线程不存在，请重新发起生成。",
                task.output_data or {},
            )
        if update_time and timezone.now() - update_time < timedelta(seconds=cls.stale_seconds()):
            return task
        return cls.fail_task(
            task,
            f"任务已中断：运行状态超过{cls.stale_seconds()}秒未更新，可能是服务重启、请求中断或执行线程已退出。",
            task.output_data or {},
        )


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
    BUILTIN_MCP_DESCRIPTION = "芒果测试平台内置 MCP 服务"
    BUILTIN_MCP_PROMPT = (
        "这是芒果测试平台内置 MCP，主要用于创建和维护平台内的 API 自动化资产。"
        "生成 API 自动化用例时优先使用它完成项目/模块/负责人/环境查询、API Info 创建或更新、"
        "API Case 创建或覆盖、步骤和场景维护、请求头、断言、提取器、数据工厂配置、执行 API Case 和查询执行结果。"
        "如果当前任务需要写入测试平台的 API 自动化用例，应优先选择这个 MCP 的工具。"
    )

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
                "copy_api_case_scenario",
                "get_api_assertion_schema",
                "get_api_assertion_methods",
                "get_api_extractor_schema",
                "generate_api_case_scenario_assertions",
                "auto_generate_api_case_scenario_schema",
                "generate_api_case_scenario_extractors",
                "create_complete_api_case",
                "run_api_case",
                "get_api_case_run_result",
                "analyze_api_case_failure",
                "get_api_case_schema",
            ],
        },
        {
            "key": "data_factory",
            "title": "数据工厂",
            "description": "数据工厂实体、字段、模板、预览、绑定和清理",
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
                "get_data_factory_execution_context",
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
            return {"key": "data_factory", "title": "数据工厂", "description": "数据工厂实体、字段、模板、预览、绑定和清理"}
        if tool_name.startswith(("search_api_", "get_api_", "create_api_", "update_api_", "delete_api_", "run_api_", "analyze_api_", "add_api_", "sort_api_", "refresh_api_", "copy_api_", "auto_generate_api_", "generate_api_")):
            return {"key": "api_automation", "title": "API自动化", "description": "API 接口、用例、场景、执行和结果分析"}
        if "_ui_" in tool_name or tool_name.startswith(("search_ui_", "get_ui_", "create_ui_", "update_ui_", "delete_ui_")):
            return {"key": "ui_automation", "title": "UI自动化", "description": "UI 自动化查询与手动绑定辅助"}
        if "functional_test" in tool_name:
            return {"key": "functional_test", "title": "功能测试", "description": "功能测试需求、用例、上下文资料、自动化绑定、统计和模块导航"}
        if "scheduled_task" in tool_name or "time_task" in tool_name:
            return {"key": "scheduled_task", "title": "定时任务", "description": "定时任务和任务明细绑定"}
        return {"key": "other", "title": "其他", "description": "未归类工具"}

    @classmethod
    def assistant_tool_categories(cls, content: str) -> set[str]:
        text = (content or "").lower()
        categories = {"project_context"}
        if any(keyword in text for keyword in ("数据工厂", "造数", "数据库", "sql", "表结构", "实体", "字段", "datasource", "factory")):
            categories.add("data_factory")
        if any(keyword in text for keyword in ("api", "接口", "case", "用例", "请求", "响应", "断言", "提取", "header", "curl")):
            categories.add("api_automation")
        if any(keyword in text for keyword in ("ui", "页面", "元素", "定位", "界面自动化")):
            categories.add("ui_automation")
        if any(keyword in text for keyword in ("功能测试", "需求列表", "需求文档", "原始case", "手工测试", "手工用例", "测试用例", "用例同步")):
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
                server.prompt = cls.BUILTIN_MCP_PROMPT
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
            prompt=cls.BUILTIN_MCP_PROMPT,
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
    def select_online_server(cls, request, preferred_server_id: int | None = None) -> tuple[AiMcpServer | None, list[dict]]:
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
            server.last_error = str(exc)[:1000]
            server.save(update_fields=["last_test_time", "last_error", "update_time"])
            return {"ok": False, "error": str(exc)}

    @classmethod
    def refresh_statuses(cls, servers, user_id: int | None = None) -> list[dict]:
        results = []
        for server in servers:
            result = cls.test_server(server, user_id)
            results.append({"id": server.id, **result})
        return results

    @classmethod
    def sync_tools(cls, server: AiMcpServer, user_id: int | None = None) -> dict:
        capabilities = ExternalMcpClient.list_capabilities(server, user_id)
        count = 0
        for item in capabilities.get("tools") or []:
            tool_name = item.get("name")
            if not tool_name:
                continue
            risk_level, write_operation, require_confirm = cls.infer_risk(tool_name)
            AiMcpTool.objects.update_or_create(
                server=server,
                name=tool_name,
                tool_type="tool",
                defaults={
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
            count += 1
        for tool_type, rows in (("resource", capabilities.get("resources") or []), ("prompt", capabilities.get("prompts") or [])):
            for item in rows:
                tool_name = item.get("name") or item.get("uri")
                if not tool_name:
                    continue
                risk_level, write_operation, require_confirm = cls.infer_risk(tool_name)
                AiMcpTool.objects.update_or_create(
                    server=server,
                    name=tool_name,
                    tool_type=tool_type,
                    defaults={
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
                count += 1
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
    def sync_builtin_tools(cls, server: AiMcpServer, user_id: int | None = None) -> dict:
        return cls.sync_tools(server, user_id)

    @staticmethod
    def call_tool(server: AiMcpServer, tool_name: str, arguments: dict | None = None, user_id: int | None = None) -> dict:
        return ExternalMcpClient.call_tool(server, tool_name, arguments or {}, user_id)

    @staticmethod
    def log_tool_call(task: AiAgentTask, tool_name: str, arguments: dict, result: dict, server: AiMcpServer | None = None):
        status = AiAgentToolCallStatusEnum.SUCCESS.value if McpService.is_tool_call_success(result) else AiAgentToolCallStatusEnum.FAIL.value
        return AiAgentToolCall.objects.create(
            task=task,
            server=server,
            tool_name=tool_name,
            arguments=mask_sensitive(arguments),
            result=mask_sensitive(result),
            status=status,
            risk_level=McpService.infer_risk(tool_name)[0],
            confirm_required=McpService.infer_risk(tool_name)[2],
            error_message="" if status == AiAgentToolCallStatusEnum.SUCCESS.value else McpService.extract_tool_call_error(result),
            start_time=timezone.now(),
            end_time=timezone.now(),
        )

    @staticmethod
    def is_tool_call_success(result: dict | None) -> bool:
        if not isinstance(result, dict):
            return False
        if result.get("isError") is True:
            return False
        if result.get("success") is False:
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
