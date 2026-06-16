from __future__ import annotations

from typing import Any

from src.apps.ai.models import (
    AiAgentContext,
    AiAgentTask,
    AiAgentTaskStep,
    AiAgentToolCall,
    AiMcpServer,
    AiMcpTool,
    AiSkill,
)
from src.apps.ai.service.core import mask_sensitive
from src.apps.ai.views.agent_context import AiAgentContextSerializer
from src.apps.ai.views.agent_task import AiAgentTaskSerializer
from src.apps.ai.views.agent_task_step import AiAgentTaskStepSerializer
from src.apps.ai.views.agent_tool_call import AiAgentToolCallSerializer
from src.apps.ai.views.mcp_server import AiMcpServerSerializer
from src.apps.ai.views.mcp_tool import AiMcpToolSerializer
from src.apps.ai.views.skill import AiSkillSerializer
from src.services.mcp_server.common import ok


MAX_PAGE_SIZE = 100


def _page(page: int = 1, page_size: int = 20) -> tuple[int, int]:
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 20), 1), MAX_PAGE_SIZE)
    return page, page_size


def _paginate(queryset, page: int = 1, page_size: int = 20):
    page, page_size = _page(page, page_size)
    total = queryset.count()
    start = (page - 1) * page_size
    return queryset[start : start + page_size], total, page, page_size


def _mask_ai_data(value: Any) -> Any:
    return mask_sensitive(value)


def _mask_record(record: dict, keys: list[str] | None = None) -> dict:
    data = dict(record)
    for key in keys or []:
        if key in data:
            data[key] = _mask_ai_data(data.get(key))
    return data


def _task_queryset():
    return AiAgentTaskSerializer.setup_eager_loading(AiAgentTask.objects.all())


def _context_queryset():
    return AiAgentContextSerializer.setup_eager_loading(AiAgentContext.objects.all())


def _server_queryset():
    return AiMcpServerSerializer.setup_eager_loading(AiMcpServer.objects.all())


def _skill_queryset():
    return AiSkillSerializer.setup_eager_loading(AiSkill.objects.all())


def _tool_queryset():
    return AiMcpToolSerializer.setup_eager_loading(AiMcpTool.objects.all())


def _step_queryset():
    return AiAgentTaskStepSerializer.setup_eager_loading(AiAgentTaskStep.objects.all())


def _tool_call_queryset():
    return AiAgentToolCallSerializer.setup_eager_loading(AiAgentToolCall.objects.all())


def _task_data(task: AiAgentTask) -> dict:
    data = AiAgentTaskSerializer(instance=task).data
    return _mask_record(data, ["input_data", "output_data"])


def _server_data(server: AiMcpServer) -> dict:
    data = AiMcpServerSerializer(instance=server).data
    return _mask_record(data, ["auth_config"])


def _context_data(context: AiAgentContext, include_snapshots: bool = False) -> dict:
    data = AiAgentContextSerializer(instance=context).data
    if include_snapshots:
        return _mask_record(data, ["source_snapshot", "result_snapshot", "skill_snapshot", "mcp_snapshot"])
    return {
        "id": data.get("id"),
        "create_time": data.get("create_time"),
        "suite_id": data.get("suite_id"),
        "manual_case_id": data.get("manual_case_id"),
        "context_type": data.get("context_type"),
        "context_hash": data.get("context_hash"),
        "summary": data.get("summary"),
        "user_instruction": data.get("user_instruction"),
        "task": data.get("task"),
        "task": data.get("task"),
        "create_user": data.get("create_user"),
    }


def _tool_call_data(tool_call: AiAgentToolCall) -> dict:
    data = AiAgentToolCallSerializer(instance=tool_call).data
    return _mask_record(data, ["arguments", "result"])


def _step_data(step: AiAgentTaskStep) -> dict:
    data = AiAgentTaskStepSerializer(instance=step).data
    return _mask_record(data, ["input_data", "output_data"])


def register_ai_query_tools(mcp):
    @mcp.tool()
    def list_ai_skills(
        skill_type: int | None = None,
        status: int | None = None,
        is_builtin: bool | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """分页查询 AI Skill。"""
        queryset = _skill_queryset()
        if skill_type is not None:
            queryset = queryset.filter(skill_type=skill_type)
        if status is not None:
            queryset = queryset.filter(status=status)
        if is_builtin is not None:
            queryset = queryset.filter(is_builtin=is_builtin)
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        items, total, page, page_size = _paginate(queryset, page, page_size)
        return ok({"items": AiSkillSerializer(instance=items, many=True).data, "total": total, "page": page, "page_size": page_size})

    @mcp.tool()
    def get_ai_skill_detail(skill_id: int) -> dict:
        """查询 AI Skill 详情，包含完整 Skill 内容。"""
        skill = _skill_queryset().get(id=skill_id)
        return ok(AiSkillSerializer(instance=skill).data)

    @mcp.tool()
    def list_ai_mcp_servers(
        status: int | None = None,
        is_builtin: bool | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """分页查询 AI MCP 服务配置。鉴权配置会脱敏。"""
        queryset = _server_queryset()
        if status is not None:
            queryset = queryset.filter(status=status)
        if is_builtin is not None:
            queryset = queryset.filter(auth_config__builtin=True) if is_builtin else queryset.exclude(auth_config__builtin=True)
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        items, total, page, page_size = _paginate(queryset, page, page_size)
        return ok({"items": [_server_data(item) for item in items], "total": total, "page": page, "page_size": page_size})

    @mcp.tool()
    def get_ai_mcp_server_detail(server_id: int, include_tools: bool = True) -> dict:
        """查询 AI MCP 服务详情，可包含该服务同步到的平台工具列表。"""
        server = _server_queryset().get(id=server_id)
        data = _server_data(server)
        if include_tools:
            tools = _tool_queryset().filter(server_id=server_id)
            data["tools"] = AiMcpToolSerializer(instance=tools, many=True).data
        return ok(data)

    @mcp.tool()
    def list_ai_mcp_tools(
        server_id: int | None = None,
        enabled: bool | None = None,
        write_operation: bool | None = None,
        risk_level: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """分页查询 AI MCP 工具快照。"""
        queryset = _tool_queryset()
        if server_id is not None:
            queryset = queryset.filter(server_id=server_id)
        if enabled is not None:
            queryset = queryset.filter(enabled=enabled)
        if write_operation is not None:
            queryset = queryset.filter(write_operation=write_operation)
        if risk_level is not None:
            queryset = queryset.filter(risk_level=risk_level)
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        items, total, page, page_size = _paginate(queryset, page, page_size)
        return ok({"items": AiMcpToolSerializer(instance=items, many=True).data, "total": total, "page": page, "page_size": page_size})

    @mcp.tool()
    def list_ai_agent_tasks(
        task_type: int | None = None,
        status: int | None = None,
        skill_id: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """分页查询 AI Agent 任务。输入输出会脱敏。"""
        queryset = _task_queryset()
        if task_type is not None:
            queryset = queryset.filter(task_type=task_type)
        if status is not None:
            queryset = queryset.filter(status=status)
        if skill_id is not None:
            queryset = queryset.filter(skill_id=skill_id)
        if keyword:
            queryset = queryset.filter(title__contains=keyword)
        items, total, page, page_size = _paginate(queryset, page, page_size)
        return ok({"items": [_task_data(item) for item in items], "total": total, "page": page, "page_size": page_size})

    @mcp.tool()
    def get_ai_agent_task_detail(task_id: int, include_steps: bool = True, include_tool_calls: bool = True) -> dict:
        """查询 AI Agent 任务详情，可包含阶段和 MCP 工具调用记录。"""
        task = _task_queryset().get(id=task_id)
        data = _task_data(task)
        if include_steps:
            steps = _step_queryset().filter(task_id=task_id)
            data["steps"] = [_step_data(item) for item in steps]
        if include_tool_calls:
            tool_calls = _tool_call_queryset().filter(task_id=task_id)
            data["tool_calls"] = [_tool_call_data(item) for item in tool_calls]
        return ok(data)

    @mcp.tool()
    def list_ai_agent_task_steps(
        task_id: int | None = None,
        status: int | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict:
        """分页查询 AI Agent 任务阶段。"""
        queryset = _step_queryset()
        if task_id is not None:
            queryset = queryset.filter(task_id=task_id)
        if status is not None:
            queryset = queryset.filter(status=status)
        items, total, page, page_size = _paginate(queryset, page, page_size)
        return ok({"items": [_step_data(item) for item in items], "total": total, "page": page, "page_size": page_size})

    @mcp.tool()
    def list_ai_agent_tool_calls(
        task_id: int | None = None,
        server_id: int | None = None,
        status: int | None = None,
        tool_name: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict:
        """分页查询 AI Agent MCP 工具调用记录。"""
        queryset = _tool_call_queryset()
        if task_id is not None:
            queryset = queryset.filter(task_id=task_id)
        if server_id is not None:
            queryset = queryset.filter(server_id=server_id)
        if status is not None:
            queryset = queryset.filter(status=status)
        if tool_name:
            queryset = queryset.filter(tool_name__contains=tool_name)
        items, total, page, page_size = _paginate(queryset, page, page_size)
        return ok({"items": [_tool_call_data(item) for item in items], "total": total, "page": page, "page_size": page_size})

    @mcp.tool()
    def list_ai_agent_contexts(
        suite_id: int | None = None,
        manual_case_id: int | None = None,
        context_type: str | None = None,
        context_hash: str | None = None,
        task_id: int | None = None,
        include_snapshots: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """分页查询 AI Agent 上下文历史。默认返回轻量信息，include_snapshots=true 时返回快照。"""
        queryset = _context_queryset()
        if suite_id is not None:
            queryset = queryset.filter(suite_id=suite_id)
        if manual_case_id is not None:
            queryset = queryset.filter(manual_case_id=manual_case_id)
        if context_type:
            queryset = queryset.filter(context_type=context_type)
        if context_hash:
            queryset = queryset.filter(context_hash=context_hash)
        if task_id is not None:
            queryset = queryset.filter(task_id=task_id)
        items, total, page, page_size = _paginate(queryset, page, page_size)
        return ok(
            {
                "items": [_context_data(item, include_snapshots=include_snapshots) for item in items],
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        )
