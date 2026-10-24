from __future__ import annotations

from typing import Any

from src.apps.ai.enums import AiMcpStatusEnum, AiMcpTransportTypeEnum, AiMcpUseTypeEnum
from src.apps.ai.models import (
    AiAgentContext,
    AiAgentTask,
    AiAgentTaskStep,
    AiAgentToolCall,
    AiMcpServer,
)
from src.apps.ai.presenters import (
    format_agent_context,
    format_agent_task,
    format_agent_task_step,
    format_agent_tool_call,
    format_mcp_server,
    format_mcp_tool,
    format_skill,
)
from src.apps.ai.selectors.querysets import AiQuerySelector
from src.apps.ai.services.core import mask_sensitive
from src.apps.ai.services.mcp_server import AiMcpServerMutationService
from src.common.exceptions import MangoServerError
from src.interfaces.mcp.common import current_user, fail, ok
from src.interfaces.mcp.exceptions import McpError

MAX_PAGE_SIZE = 100


def _page(page: int = 1, page_size: int = 10) -> tuple[int, int]:
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 10), 1), MAX_PAGE_SIZE)
    return page, page_size


def _paginate(queryset, page: int = 1, page_size: int = 10):
    page, page_size = _page(page, page_size)
    total = queryset.count()
    start = (page - 1) * page_size
    return queryset[start: start + page_size], total, page, page_size


def _mask_ai_data(value: Any) -> Any:
    return mask_sensitive(value)


def _mask_record(record: dict, keys: list[str] | None = None) -> dict:
    data = dict(record)
    for key in keys or []:
        if key in data:
            data[key] = _mask_ai_data(data.get(key))
    return data


def _task_queryset():
    return AiQuerySelector.agent_task_details()


def _context_queryset():
    return AiQuerySelector.agent_context_details()


def _server_queryset():
    return AiQuerySelector.mcp_server_details()


def _skill_queryset():
    return AiQuerySelector.skill_details()


def _tool_queryset():
    return AiQuerySelector.mcp_tool_details()


def _step_queryset():
    return AiQuerySelector.agent_task_step_details()


def _tool_call_queryset():
    return AiQuerySelector.agent_tool_call_details()


def _task_data(task: AiAgentTask) -> dict:
    data = format_agent_task(task)
    return _mask_record(data, ["input_data", "output_data"])


def _server_data(server: AiMcpServer) -> dict:
    data = format_mcp_server(server)
    return _mask_record(data, ["auth_config"])


def _context_data(context: AiAgentContext, include_snapshots: bool = False) -> dict:
    data = format_agent_context(context)
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
    data = format_agent_tool_call(tool_call)
    return _mask_record(data, ["arguments", "result"])


def _step_data(step: AiAgentTaskStep) -> dict:
    data = format_agent_task_step(step)
    return _mask_record(data, ["input_data", "output_data"])


def register_ai_query_tools(mcp):
    @mcp.tool()
    def list_ai_skills(
            skill_type: int | None = None,
            status: int | None = None,
            is_builtin: bool | None = None,
            keyword: str | None = None,
            page: int = 1,
            page_size: int = 10,
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
        return ok({"items": format_skill(items, many=True), "total": total, "page": page, "page_size": page_size})

    @mcp.tool()
    def get_ai_skill_detail(skill_id: int) -> dict:
        """查询 AI Skill 详情，包含完整 Skill 内容。"""
        skill = _skill_queryset().get(id=skill_id)
        return ok(format_skill(skill))

    @mcp.tool()
    def list_ai_mcp_servers(
            status: int | None = None,
            is_builtin: bool | None = None,
            keyword: str | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分页查询 AI MCP 服务配置。鉴权配置会脱敏。"""
        queryset = _server_queryset()
        if status is not None:
            queryset = queryset.filter(status=status)
        if is_builtin is not None:
            queryset = queryset.filter(auth_config__builtin=True) if is_builtin else queryset.exclude(
                auth_config__builtin=True)
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        items, total, page, page_size = _paginate(queryset, page, page_size)
        return ok(
            {"items": [_server_data(item) for item in items], "total": total, "page": page, "page_size": page_size})

    @mcp.tool()
    def create_ai_mcp_server(
            name: str,
            server_url: str | None = None,
            endpoint_path: str | None = None,
            project_product_id: int | None = None,
            module_id: int | None = None,
            transport_type: int = AiMcpTransportTypeEnum.STREAMABLE_HTTP.value,
            auth_type: int = 0,
            auth_config: dict | None = None,
            type: int = AiMcpUseTypeEnum.API_AUTOMATION.value,
            description: str | None = None,
            prompt: str | None = None,
            status: int = AiMcpStatusEnum.ENABLED.value,
            sync_after_create: bool = False,
            test_env: int | None = None,
    ) -> dict:
        """创建 AI MCP Server 配置。

        用于把外部 MCP 服务登记到平台。server_url 和 endpoint_path 二选一，endpoint_path 会按服务地址保存。
        type 建议传 1（API自动化）或 2（通用）；只有API自动化/通用的 Tool 才能导入 API Info。
        sync_after_create=True 时会创建后立即连接服务并同步 tools/resources/prompts。
        """
        payload = {
            "project_product": project_product_id,
            "module": module_id,
            "type": type,
            "name": name,
            "server_url": server_url or endpoint_path,
            "transport_type": transport_type,
            "auth_type": auth_type,
            "auth_config": auth_config or {},
            "description": description,
            "prompt": prompt or "用于API自动化的 MCP 服务，可同步 Tool 后导入为接口定义并编排到 API case。",
            "status": status,
            "create_user": current_user().id,
            "update_user": current_user().id,
        }
        if not payload["server_url"]:
            return fail("创建 MCP Server 必须提供 server_url 或 endpoint_path", "MCP_SERVER_URL_REQUIRED")
        result = AiMcpServerMutationService.create(
            payload,
            current_user().id,
            sync_after_save=sync_after_create,
            test_env=test_env,
        )
        if result.errors:
            return fail("MCP Server创建参数校验失败", "MCP_SERVER_CREATE_FAILED", result.errors)
        server = result.instance
        data = _server_data(server)
        if result.sync_error:
            return fail(result.sync_error, "MCP_SERVER_SYNC_FAILED", {"server": data})
        if sync_after_create and not result.test_result.get("ok"):
            return fail(
                "MCP Server连接测试失败",
                "MCP_SERVER_CONNECT_FAILED",
                {"server": data, "test_result": result.test_result},
            )
        if result.sync_result is not None:
            data["sync_result"] = result.sync_result
        return ok(data, "MCP Server创建成功")

    @mcp.tool()
    def update_ai_mcp_server(
            server_id: int,
            name: str | None = None,
            server_url: str | None = None,
            endpoint_path: str | None = None,
            project_product_id: int | None = None,
            module_id: int | None = None,
            transport_type: int | None = None,
            auth_type: int | None = None,
            auth_config: dict | None = None,
            type: int | None = None,
            description: str | None = None,
            prompt: str | None = None,
            status: int | None = None,
            sync_after_update: bool = False,
            test_env: int | None = None,
    ) -> dict:
        """更新 AI MCP Server 配置。

        auth_config 采用增量合并；传入值为 "***" 的密文字段会保留原值。
        更新服务地址或鉴权后可传 sync_after_update=True 立即重新同步工具。
        """
        payload = {}
        field_values = {
            "name": name,
            "server_url": server_url or endpoint_path,
            "project_product": project_product_id,
            "module": module_id,
            "transport_type": transport_type,
            "auth_type": auth_type,
            "type": type,
            "description": description,
            "prompt": prompt,
            "status": status,
        }
        for key, value in field_values.items():
            if value is not None:
                payload[key] = value
        if auth_config is not None:
            payload["auth_config"] = auth_config
        result = AiMcpServerMutationService.update(
            server_id,
            payload,
            current_user().id,
            sync_after_save=sync_after_update,
            test_env=test_env,
        )
        if result.errors:
            return fail("MCP Server更新参数校验失败", "MCP_SERVER_UPDATE_FAILED", result.errors)
        server = result.instance
        data = _server_data(server)
        if result.sync_error:
            return fail(result.sync_error, "MCP_SERVER_SYNC_FAILED", {"server": data})
        if sync_after_update and not result.test_result.get("ok"):
            return fail(
                "MCP Server连接测试失败",
                "MCP_SERVER_CONNECT_FAILED",
                {"server": data, "test_result": result.test_result},
            )
        if result.sync_result is not None:
            data["sync_result"] = result.sync_result
        return ok(data, "MCP Server更新成功")

    @mcp.tool()
    def sync_ai_mcp_server_tools(server_id: int, test_env: int | None = None) -> dict:
        """连接 MCP Server 并同步 tools/resources/prompts 到 AiMcpTool。

        同步后可用 list_ai_mcp_tools 查询 Tool，再调用 import_mcp_tool_to_api_info 导入为接口定义。
        test_env 非空时按环境同步快照；为空时会停用远端已不存在的旧 Tool。
        """
        try:
            mutation_result = AiMcpServerMutationService.sync_tools(
                server_id,
                current_user().id,
                test_env=test_env,
            )
            if mutation_result.sync_error:
                return fail(mutation_result.sync_error, "MCP_SERVER_SYNC_FAILED")
            if not mutation_result.test_result.get("ok"):
                return fail(mutation_result.test_result, "MCP_SERVER_CONNECT_FAILED")
        except MangoServerError as error:
            return fail(error.msg, "MCP_SERVER_SYNC_FAILED")
        except McpError as error:
            return fail(str(error), "MCP_SERVER_SYNC_FAILED")
        except Exception as exc:
            return fail(str(exc), "MCP_SERVER_SYNC_FAILED")
        return ok(mutation_result.sync_result, "MCP Server工具同步完成")

    @mcp.tool()
    def get_ai_mcp_server_detail(server_id: int) -> dict:
        """查询 AI MCP 服务详情；工具快照请使用 list_ai_mcp_tools 分页查询。"""
        server = _server_queryset().get(id=server_id)
        return ok(_server_data(server))

    @mcp.tool()
    def list_ai_mcp_tools(
            server_id: int | None = None,
            enabled: bool | None = None,
            write_operation: bool | None = None,
            risk_level: int | None = None,
            keyword: str | None = None,
            page: int = 1,
            page_size: int = 10,
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
        return ok({"items": format_mcp_tool(items, many=True), "total": total, "page": page, "page_size": page_size})

    @mcp.tool()
    def list_ai_agent_tasks(
            task_type: int | None = None,
            status: int | None = None,
            skill_id: int | None = None,
            keyword: str | None = None,
            page: int = 1,
            page_size: int = 10,
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
            page_size: int = 10,
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
            page_size: int = 10,
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
        return ok(
            {"items": [_tool_call_data(item) for item in items], "total": total, "page": page, "page_size": page_size})

    @mcp.tool()
    def list_ai_agent_contexts(
            suite_id: int | None = None,
            manual_case_id: int | None = None,
            context_type: str | None = None,
            context_hash: str | None = None,
            task_id: int | None = None,
            include_snapshots: bool = False,
            page: int = 1,
            page_size: int = 10,
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
