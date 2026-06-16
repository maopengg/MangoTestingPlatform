# -*- coding: utf-8 -*-
import json

from src.apps.ai.agent.functional_case.schema import build_system_prompt
from src.apps.ai.models import AiAgentTask, AiSkill
from src.apps.ai.service.core import AiTaskService, extract_ai_json
from src.apps.system.service.ai.client import AiService


class FunctionalCaseDesignAnalyzer:
    @staticmethod
    def text_window(text: str, limit: int) -> str:
        content = text or ""
        if len(content) <= limit:
            return content
        head_size = max(limit * 2 // 3, 1)
        tail_size = max(limit - head_size, 1)
        return (
            content[:head_size]
            + f"\n\n...中间内容已省略，原文总长度 {len(content)} 字符...\n\n"
            + content[-tail_size:]
        )

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
                "content": (
                    "请先做需求理解，不要生成测试用例。"
                    "输出 JSON：{business_goals:[], user_roles:[], main_flows:[], branch_flows:[], acceptance_points:[], data_points:[], risks:[], warnings:[]}。\n"
                    f"补充要求：{user_instruction}\n"
                    f"需求/上下文资料：\n{cls.text_window(requirement_context, 24000)}\n"
                    f"原始用例资料摘要：\n{cls.text_window(source_content, 6000)}"
                ),
            },
        ]
        return extract_ai_json(AiService.json_chat(messages, max_tokens=6000))

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
                "content": (
                    "请分析原始用例已经覆盖了哪些内容，不要生成新用例。"
                    "输出 JSON：{covered_acceptance_points:[], covered_case_titles:[], normal:[], abnormal:[], boundary:[], permission:[], data:[], flow:[], weak_points:[], warnings:[]}。\n"
                    f"补充要求：{user_instruction}\n"
                    f"需求理解：{json.dumps(requirement_analysis, ensure_ascii=False)[:16000]}\n"
                    f"原始用例资料：\n{cls.text_window(source_content, 24000)}"
                ),
            },
        ]
        return extract_ai_json(AiService.json_chat(messages, max_tokens=8000))

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
                "content": (
                    "请基于需求理解和已有覆盖做差异分析，并给出后续生成策略。"
                    "输出 JSON：{missing_acceptance_points:[], missing_normal:[], missing_abnormal:[], missing_boundary:[], missing_permission:[], missing_data:[], missing_flow:[], generation_outline:[{group_name, expected_case_count, case_titles:[]}], dedupe_rules:[], warnings:[]}。\n"
                    f"补充要求：{user_instruction}\n"
                    f"需求理解：{json.dumps(requirement_analysis, ensure_ascii=False)[:18000]}\n"
                    f"已有覆盖：{json.dumps(existing_coverage, ensure_ascii=False)[:18000]}"
                ),
            },
        ]
        return extract_ai_json(AiService.json_chat(messages, max_tokens=8000))
