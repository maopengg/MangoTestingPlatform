# -*- coding: utf-8 -*-
import json

from src.apps.ai.agent.functional_case.prompt import build_system_prompt
from src.apps.ai.context import StructuredContextCompiler
from src.apps.ai.model_gateway.client import AgentModelGateway
from src.apps.ai.models import AiAgentTask, AiSkill
from src.apps.ai.services.core import AiTaskService, extract_ai_json
from src.common.prompts.functional_test import render_functional_case_prompt


class FunctionalCaseDesignAnalyzer:
    @classmethod
    def analyze_requirement(
            cls,
            *,
            requirement_context: str,
            source_content: str,
            user_instruction: str,
            skill: AiSkill | None,
            ai_role: str | None,
            task: AiAgentTask | None = None,
    ) -> dict:
        if task:
            AiTaskService.update_progress(task, 18, "请求已经发给 AI", "正在理解需求目标、角色、流程和验收点")
        messages = [
            {"role": "system", "content": build_system_prompt(skill, ai_role)},
            {
                "role": "user",
                "content": render_functional_case_prompt(
                    "requirement_analysis",
                    user_instruction=user_instruction,
                    requirement_context=StructuredContextCompiler.select(
                        requirement_context, "业务目标 用户角色 权限 主流程 分支流程 状态 规则 验收点 风险", 24000
                    ),
                    source_content=StructuredContextCompiler.select(
                        source_content, "验收点 已有用例 覆盖 前置条件 测试点", 6000
                    ),
                ),
            },
        ]
        return cls.normalize_requirement_model(
            extract_ai_json(
                AgentModelGateway.json_chat(task=task, messages=messages, max_tokens=6000),
                task=task,
            )
        )

    @classmethod
    def analyze_existing_coverage(
            cls,
            *,
            requirement_analysis: dict,
            source_content: str,
            user_instruction: str,
            skill: AiSkill | None,
            ai_role: str | None,
            task: AiAgentTask | None = None,
    ) -> dict:
        if task:
            AiTaskService.update_progress(task, 28, "请求已经发给 AI", "正在识别原始用例已有覆盖")
        messages = [
            {"role": "system", "content": build_system_prompt(skill, ai_role)},
            {
                "role": "user",
                "content": render_functional_case_prompt(
                    "existing_coverage",
                    user_instruction=user_instruction,
                    requirement_analysis=json.dumps(requirement_analysis, ensure_ascii=False)[:16000],
                    source_content=StructuredContextCompiler.select(
                        source_content, json.dumps(requirement_analysis, ensure_ascii=False)[:4000], 24000
                    ),
                ),
            },
        ]
        return extract_ai_json(
            AgentModelGateway.json_chat(task=task, messages=messages, max_tokens=8000),
            task=task,
        )

    @classmethod
    def analyze_gap(
            cls,
            *,
            requirement_analysis: dict,
            existing_coverage: dict,
            user_instruction: str,
            skill: AiSkill | None,
            ai_role: str | None,
            task: AiAgentTask | None = None,
    ) -> dict:
        if task:
            AiTaskService.update_progress(task, 36, "请求已经发给 AI", "正在分析缺失场景和生成策略")
        messages = [
            {"role": "system", "content": build_system_prompt(skill, ai_role)},
            {
                "role": "user",
                "content": render_functional_case_prompt(
                    "gap_analysis",
                    user_instruction=user_instruction,
                    requirement_analysis=json.dumps(requirement_analysis, ensure_ascii=False)[:18000],
                    existing_coverage=json.dumps(existing_coverage, ensure_ascii=False)[:18000],
                ),
            },
        ]
        return extract_ai_json(
            AgentModelGateway.json_chat(task=task, messages=messages, max_tokens=8000),
            task=task,
        )

    @staticmethod
    def normalize_requirement_model(payload: dict) -> dict:
        result = dict(payload or {})
        criteria = result.get("acceptance_criteria") or result.pop("acceptance_points", []) or []
        result["acceptance_criteria"] = [
            {
                "criterion_id": f"AC-{index:03d}",
                "description": item.get("description") if isinstance(item, dict) else str(item),
                "source_refs": item.get("source_refs") or [] if isinstance(item, dict) else [],
            }
            for index, item in enumerate(criteria, start=1)
            if (item.get("description") if isinstance(item, dict) else str(item)).strip()
        ]
        result.setdefault("actors", result.pop("user_roles", []) or [])
        result.setdefault("permissions", [])
        result.setdefault("preconditions", [])
        result.setdefault("main_flows", [])
        result.setdefault("alternative_flows", result.pop("branch_flows", []) or [])
        result.setdefault("state_transitions", [])
        result.setdefault("business_rules", [])
        result.setdefault("data_entities", result.pop("data_points", []) or [])
        result.setdefault("risks", [])
        ambiguities = result.get("ambiguities") or result.pop("warnings", []) or []
        result["ambiguities"] = [
            item
            if isinstance(item, dict)
            else {
                "description": str(item),
                "severity": "risk",
                "requires_confirmation": False,
                "options": [],
                "source_refs": [],
            }
            for item in ambiguities
            if str(item).strip()
        ]
        return result

    @staticmethod
    def finalize_coverage_matrix(requirement_model: dict, existing_coverage: dict, gap: dict) -> dict:
        covered_text = " ".join(
            str(item) for item in existing_coverage.get("covered_acceptance_points") or []
        ).lower()
        missing_text = " ".join(str(item) for item in gap.get("missing_acceptance_points") or []).lower()
        criteria = []
        planned_titles = [
            title
            for group in gap.get("generation_outline") or []
            if isinstance(group, dict)
            for title in group.get("case_titles") or []
        ]
        for item in requirement_model.get("acceptance_criteria") or []:
            description = str(item.get("description") or "")
            normalized = description.lower()
            coverage = "covered" if normalized and normalized in covered_text else "missing" if normalized and normalized in missing_text else "partial"
            criteria.append(
                {
                    "criterion_id": item.get("criterion_id"),
                    "description": description,
                    "coverage": coverage,
                    "existing_case_refs": [],
                    "planned_case_refs": planned_titles if coverage != "covered" else [],
                    "missing_dimensions": [],
                }
            )
        result = dict(gap or {})
        result["criteria"] = criteria
        result["dimension_summary"] = {
            "normal": len(gap.get("missing_normal") or []),
            "exception": len(gap.get("missing_abnormal") or []),
            "boundary": len(gap.get("missing_boundary") or []),
            "permission": len(gap.get("missing_permission") or []),
            "data": len(gap.get("missing_data") or []),
            "flow": len(gap.get("missing_flow") or []),
        }
        return result
