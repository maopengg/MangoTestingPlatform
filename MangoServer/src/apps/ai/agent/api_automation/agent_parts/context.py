# -*- coding: utf-8 -*-
from src.apps.ai.enums.role import AgentRole
from src.apps.ai.models import AiAgentTask, AiAgentTaskItem
from src.apps.ai.services.agent.context import AgentContextService


class ApiAutomationContextMixin:
    @classmethod
    def save_generation_context(
            cls,
            suite,
            manual_case,
            task_snapshot: dict,
            context_package: dict,
            selected_context_keys: list[int],
            plan: dict,
            user_id: int | None,
            status: int,
            user_instruction: str = "",
            error_message: str = "",
    ):
        task = AiAgentTask.objects.filter(id=task_snapshot.get("id")).first()
        AgentContextService.save_context(
            suite_id=suite.id,
            manual_case_id=manual_case.id,
            context_type="api_case_plan",
            context_hash=context_package["context_hash"],
            source_snapshot={
                "selected_context_keys": selected_context_keys,
                "content": f"复用上下文：{context_package['reuse_context_id']}"
                if context_package.get("reuse_context")
                else (context_package.get("context_text") or "")[:60000],
                "reuse_context": context_package.get("reuse_context"),
                "reuse_context_id": context_package.get("reuse_context_id"),
                "role": task_snapshot.get("input_data", {}).get("role_snapshot") or AgentRole.snapshot(
                    task_snapshot.get("input_data", {}).get("ai_role") or cls.fixed_role),
            },
            result_snapshot={
                "task_id": task_snapshot.get("id"),
                "context_hash": context_package.get("context_hash"),
                "mcp_server_ids": plan.get("mcp_server_ids") or [],
                "mcp_server_names": plan.get("mcp_server_names") or [],
                "mcp_server_prompts": plan.get("mcp_server_prompts") or {},
                "ai_role": plan.get("ai_role") or "api_automation_expert",
                "role": task_snapshot.get("input_data", {}).get("role_snapshot") or AgentRole.snapshot(
                    task_snapshot.get("input_data", {}).get("ai_role") or cls.fixed_role),
                "tool_calls": plan.get("tool_calls") or [],
                "plan": plan,
                "case_title": manual_case.title,
                "case_no": manual_case.case_no,
                "status": status,
            },
            summary=(error_message or plan.get("diff_summary") or "")[:60000],
            task=task,
            skill_snapshot=task_snapshot.get("input_data", {}).get("skill_snapshot") or {},
            mcp_snapshot={
                "mcp_server_ids": plan.get("mcp_server_ids") or [],
                "mcp_server_names": plan.get("mcp_server_names") or [],
                "mcp_server_prompts": plan.get("mcp_server_prompts") or {},
            },
            user_instruction=user_instruction or "",
            user_id=user_id,
        )

    @classmethod
    def save_batch_generation_context(
            cls,
            suite,
            task_snapshot: dict,
            context_package: dict,
            selected_context_keys: list[int],
            output: dict,
            user_id: int | None,
            status: int,
            user_instruction: str = "",
            error_message: str = "",
    ):
        task = AiAgentTask.objects.filter(id=task_snapshot.get("id")).first()
        input_data = task_snapshot.get("input_data") or {}
        item_snapshots = []
        if task:
            case_snapshots = {
                item.get("id"): item
                for item in input_data.get("manual_case_snapshots") or []
            }
            for item in AiAgentTaskItem.objects.filter(task=task).order_by("item_order", "id"):
                case_snapshot = case_snapshots.get(item.manual_case_id) or {}
                item_snapshots.append(
                    {
                        "manual_case_id": item.manual_case_id,
                        "case_no": case_snapshot.get("case_no"),
                        "title": case_snapshot.get("title"),
                        "status": item.status,
                        "attempt_no": item.attempt_no,
                        "api_case_id": item.api_case_id,
                        "execution_record_id": item.execution_record_id,
                        "summary": (item.result_summary or {}).get("summary") or "",
                        "error_message": item.error_message or "",
                    }
                )
        summary = error_message or f"批量生成API自动化完成：成功 {output.get('success_count', 0)}，失败 {output.get('fail_count', 0)}，共 {output.get('total', 0)}"
        AgentContextService.save_context(
            suite_id=suite.id,
            manual_case_id=None,
            context_type="api_case_plan",
            context_hash=context_package["context_hash"],
            source_snapshot={
                "selected_context_keys": selected_context_keys,
                "content": f"复用上下文：{context_package['reuse_context_id']}"
                if context_package.get("reuse_context")
                else (context_package.get("context_text") or "")[:60000],
                "reuse_context": context_package.get("reuse_context"),
                "reuse_context_id": context_package.get("reuse_context_id"),
                "role": input_data.get("role_snapshot") or AgentRole.snapshot(
                    input_data.get("ai_role") or cls.fixed_role),
            },
            result_snapshot={
                "mode": "batch",
                "task_id": task_snapshot.get("id"),
                "context_hash": context_package.get("context_hash"),
                "mcp_server_ids": input_data.get("mcp_server_ids") or [],
                "mcp_server_names": input_data.get("mcp_server_names") or [],
                "mcp_server_prompts": input_data.get("mcp_server_prompts") or {},
                "ai_role": input_data.get("ai_role") or "api_automation_expert",
                "role": input_data.get("role_snapshot") or AgentRole.snapshot(
                    input_data.get("ai_role") or cls.fixed_role),
                "items": item_snapshots,
                "total": output.get("total") or 0,
                "success_count": output.get("success_count") or 0,
                "fail_count": output.get("fail_count") or 0,
                "status": status,
            },
            summary=summary[:60000],
            task=task,
            skill_snapshot=input_data.get("skill_snapshot") or {},
            mcp_snapshot={
                "mcp_server_ids": input_data.get("mcp_server_ids") or [],
                "mcp_server_names": input_data.get("mcp_server_names") or [],
                "mcp_server_prompts": input_data.get("mcp_server_prompts") or {},
            },
            user_instruction=user_instruction or "",
            user_id=user_id,
        )
