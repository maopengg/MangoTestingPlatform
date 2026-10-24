# -*- coding: utf-8 -*-
from src.apps.ai.agent.functional_case.prompt import build_system_prompt
from src.apps.ai.context import StructuredContextCompiler
from src.apps.ai.model_gateway.client import AgentModelGateway
from src.apps.ai.models import AiAgentTask, AiSkill
from src.apps.ai.services.core import AiTaskService, extract_ai_json
from src.common.prompts.functional_test import render_functional_case_prompt


class FunctionalCaseOutlinePlanner:
    @classmethod
    def build_outline(
            cls,
            *,
            source_content: str,
            requirement_context: str,
            user_instruction: str,
            skill: AiSkill | None,
            ai_role: str | None,
            task: AiAgentTask | None = None,
    ) -> dict:
        if task:
            AiTaskService.update_progress(task, 22, "请求已经发给 AI", "正在拆解业务场景和用例目录")
        messages = [
            {"role": "system", "content": build_system_prompt(skill, ai_role)},
            {
                "role": "user",
                "content": render_functional_case_prompt(
                    "outline",
                    user_instruction=user_instruction,
                    requirement_context=StructuredContextCompiler.select(
                        requirement_context, "业务目标 角色 权限 流程 状态 规则 验收点 风险", 8000
                    ),
                    source_content=StructuredContextCompiler.select(
                        source_content, "已有用例 测试点 异常 边界 权限 数据 流程", 24000
                    ),
                ),
            },
        ]
        response = AgentModelGateway.json_chat(task=task, messages=messages, max_tokens=6000)
        payload = extract_ai_json(response, task=task)
        outline = payload.get("outline") if isinstance(payload, dict) else []
        if not isinstance(outline, list) or not outline:
            outline = [{"group_name": "默认场景", "expected_case_count": 0, "case_titles": []}]
        return {"suite": payload.get("suite") or {}, "outline": outline, "warnings": payload.get("warnings") or []}

    @staticmethod
    def compose_case_plan(
            requirement_model: dict,
            existing_inventory: dict,
            coverage_matrix: dict,
            *,
            preserve_existing: bool = False,
    ) -> dict:
        groups = []
        existing_titles = [
            str(item).strip()
            for item in existing_inventory.get("covered_case_titles") or []
            if str(item).strip()
        ]
        if preserve_existing and existing_titles:
            groups.append(
                {
                    "group_name": "保留并规范化已有用例",
                    "expected_case_count": len(existing_titles),
                    "case_titles": existing_titles,
                    "purpose": "preserve_existing",
                }
            )
        for item in coverage_matrix.get("generation_outline") or []:
            if not isinstance(item, dict):
                continue
            groups.append(
                {
                    "group_name": item.get("group_name") or "覆盖缺口",
                    "expected_case_count": int(
                        item.get("expected_case_count") or len(item.get("case_titles") or []) or 1),
                    "case_titles": item.get("case_titles") or [],
                    "purpose": "fill_gap",
                }
            )
        return {
            "suite": {},
            "outline": groups,
            "requirement_model": requirement_model,
            "coverage_matrix": coverage_matrix,
            "warnings": coverage_matrix.get("warnings") or [],
        }
