# -*- coding: utf-8 -*-
import hashlib
import json
from datetime import timedelta

import time
from django.utils import timezone

from src.apps.ai.enums import AiAgentToolCallStatusEnum
from src.apps.ai.exceptions import ai_service_error
from src.apps.ai.models import AiAgentToolCall
from src.apps.ai.services.agent.budget import AgentBudgetService
from src.apps.ai.services.core import McpService, mask_sensitive
from src.apps.auto_api.selectors.querysets import ApiQuerySelector


class AgentMcpToolRunner:
    UNCERTAIN_PREFIX = "MCP_WRITE_RESULT_UNCERTAIN"

    @staticmethod
    def external_asset_ids(value, *, limit: int = 50) -> dict:
        result = {}

        def walk(item, path=""):
            if len(result) >= limit:
                return
            if isinstance(item, dict):
                for key, child in item.items():
                    child_path = f"{path}.{key}" if path else str(key)
                    normalized = str(key).lower()
                    if normalized == "id" or normalized.endswith("_id"):
                        if isinstance(child, (int, str)) and str(child).strip():
                            result[child_path] = child
                    walk(child, child_path)
            elif isinstance(item, list):
                for index, child in enumerate(item[:20]):
                    walk(child, f"{path}[{index}]")

        walk(value)
        return result

    @classmethod
    def call(cls, task, tool, arguments: dict | None = None, user_id: int | None = None):
        arguments = arguments or {}
        task_item_id = getattr(task, "active_task_item_id", None)
        stage_key = getattr(task, "current_step_key", None)
        request_hash = hashlib.sha256(
            json.dumps(arguments, sort_keys=True, default=str).encode()
        ).hexdigest()
        schema_hash = hashlib.sha256(
            json.dumps(tool.input_schema or {}, sort_keys=True, default=str).encode()
        ).hexdigest()
        key_source = ":".join(
            str(item or "")
            for item in (task.id, task_item_id, stage_key, tool.server_id, tool.name, request_hash)
        )
        idempotency_key = hashlib.sha256(key_source.encode()).hexdigest()
        previous_query = AiAgentToolCall.objects.filter(
            task=task,
            idempotency_key=idempotency_key,
        ).order_by("-id")
        if tool.write_operation:
            previous_success = previous_query.filter(
                status=AiAgentToolCallStatusEnum.SUCCESS.value
            ).first()
            if previous_success and not tool.name.startswith(("run_", "execute_", "debug_run_")):
                task.last_tool_call_id = previous_success.id
                return previous_success.result or {}
            uncertain = previous_query.filter(
                error_message__startswith=cls.UNCERTAIN_PREFIX,
            ).first()
            if uncertain:
                recovered = cls.recover_builtin_write(tool, arguments, uncertain)
                if recovered:
                    cls.finish_record(uncertain, recovered, time.monotonic(), schema_hash)
                    task.last_tool_call_id = uncertain.id
                    return recovered
                raise ai_service_error(
                    "上一次 MCP 写操作在返回前中断，平台无法确认是否已写入，已阻止自动重复调用。"
                    f"请先核对工具 {tool.name} 的真实资产，或修改参数后重新执行"
                )

        AgentBudgetService.before_mcp_call(task)
        started_at = timezone.now()
        started = time.monotonic()
        record = AiAgentToolCall.objects.create(
            task=task,
            task_item_id=task_item_id,
            server=tool.server,
            tool_name=tool.name,
            arguments=mask_sensitive(arguments),
            result={},
            status=AiAgentToolCallStatusEnum.FAIL.value,
            risk_level=tool.risk_level,
            confirm_required=tool.require_confirm,
            error_message=(f"{cls.UNCERTAIN_PREFIX}: 调用已发出，尚未确认返回" if tool.write_operation else "调用中"),
            start_time=started_at,
            stage_key=stage_key,
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            mcp_tool_schema_hash=schema_hash,
        )
        task.last_tool_call_id = record.id
        try:
            result = McpService.call_tool(tool.server, tool.name, arguments, user_id)
        except Exception as exc:
            record.end_time = timezone.now()
            record.duration_ms = round((time.monotonic() - started) * 1000)
            record.error_message = (
                f"{cls.UNCERTAIN_PREFIX}: {exc}" if tool.write_operation else str(exc)
            )[:1000]
            record.save(update_fields=["end_time", "duration_ms", "error_message", "update_time"])
            raise
        cls.finish_record(record, result, started, schema_hash)
        return result

    @classmethod
    def finish_record(cls, record, result: dict, started: float, schema_hash: str):
        status = (
            AiAgentToolCallStatusEnum.SUCCESS.value
            if McpService.is_tool_call_success(result)
            else AiAgentToolCallStatusEnum.FAIL.value
        )
        record.result = mask_sensitive(result or {})
        record.status = status
        record.error_message = (
            "" if status == AiAgentToolCallStatusEnum.SUCCESS.value else McpService.extract_tool_call_error(result)
        )
        record.end_time = timezone.now()
        record.duration_ms = round((time.monotonic() - started) * 1000)
        record.result_hash = hashlib.sha256(
            json.dumps(result or {}, sort_keys=True, default=str).encode()
        ).hexdigest()
        record.mcp_tool_schema_hash = schema_hash
        record.external_asset_ids = cls.external_asset_ids(result)
        record.save(
            update_fields=[
                "result",
                "status",
                "error_message",
                "end_time",
                "duration_ms",
                "result_hash",
                "mcp_tool_schema_hash",
                "external_asset_ids",
                "update_time",
            ]
        )

    @staticmethod
    def recover_builtin_write(tool, arguments: dict, record) -> dict | None:
        if not (tool.server.auth_config or {}).get("builtin"):
            return None
        since = (record.start_time or record.create_time) - timedelta(seconds=5)
        if tool.name in {"create_api_case", "create_complete_api_case"}:
            name = arguments.get("name") or arguments.get("case_name")
            candidates = ApiQuerySelector.api_case().filter(
                project_product_id=arguments.get("project_product_id"),
                module_id=arguments.get("module_id"),
                name=name,
                create_time__gte=since,
            ).order_by("id")
            if candidates.count() == 1:
                case = candidates.first()
                return {"success": True, "recovered": True, "case_id": case.id, "api_case_id": case.id}
        if tool.name in {"create_api_info", "create_api_info_from_curl"}:
            filters = {
                "project_product_id": arguments.get("project_product_id"),
                "module_id": arguments.get("module_id"),
                "create_time__gte": since,
            }
            for key in ("name", "url", "method"):
                if arguments.get(key) not in (None, ""):
                    filters[key] = arguments[key]
            candidates = ApiQuerySelector.api_info().filter(**filters).order_by("id")
            if candidates.count() == 1:
                api_info = candidates.first()
                return {"success": True, "recovered": True, "api_info_id": api_info.id}
        if tool.name == "add_api_case_step":
            candidates = ApiQuerySelector.api_case_detailed().filter(
                case_id=arguments.get("case_id"),
                api_info_id=arguments.get("api_info_id"),
                create_time__gte=since,
            ).order_by("id")
            if candidates.count() == 1:
                step = candidates.first()
                return {"success": True, "recovered": True, "step_id": step.id, "case_id": step.case_id}
        if tool.name == "create_api_case_scenario":
            candidates = ApiQuerySelector.api_case_detailed_parameter().filter(
                case_detailed_id=arguments.get("step_id"),
                name=arguments.get("name"),
                create_time__gte=since,
            ).order_by("id")
            if candidates.count() == 1:
                scenario = candidates.first()
                return {"success": True, "recovered": True, "scenario_id": scenario.id}
        return None
