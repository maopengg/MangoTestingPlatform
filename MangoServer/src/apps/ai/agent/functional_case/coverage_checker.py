# -*- coding: utf-8 -*-
import json

from src.apps.ai.agent.functional_case.schema import CASE_SCHEMA_PROMPT, build_system_prompt
from src.apps.ai.models import AiAgentTask, AiSkill
from src.apps.ai.service.core import AiTaskService, extract_ai_json
from src.apps.system.service.ai.client import AiService


class FunctionalCaseCoverageChecker:
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
    def coverage_check_and_patch(
        cls,
        *,
        generated_payload: dict,
        source_content: str,
        requirement_context: str,
        outline: dict,
        user_instruction: str,
        skill: AiSkill | None,
        ai_role: str | None,
        task: AiAgentTask | None = None,
    ) -> dict:
        if task:
            AiTaskService.update_progress(task, 68, "请求已经发给 AI", "正在核对遗漏场景并补漏")
        case_digest = [
            {
                "case_no": item.get("case_no"),
                "title": item.get("title"),
                "test_point": item.get("test_point"),
                "scenario_type": item.get("scenario_type"),
            }
            for item in (generated_payload.get("cases") or [])
        ]
        messages = [
            {"role": "system", "content": build_system_prompt(skill, ai_role)},
            {
                "role": "user",
                "content": (
                    "请检查已生成用例是否遗漏需求、原始用例或场景大纲中的内容。"
                    "必须重点核对差异分析中的缺失项是否都已覆盖。只输出需要新增补漏的 cases；如果没有遗漏，cases 输出空数组。"
                    f"\n补充要求：{user_instruction}"
                    f"\n测试设计分析：{json.dumps(outline, ensure_ascii=False)[:16000]}"
                    f"\n已生成用例摘要：{json.dumps(case_digest, ensure_ascii=False)[:24000]}"
                    f"\n需求文档：\n{cls.text_window(requirement_context, 8000)}"
                    f"\n原始资料：\n{cls.text_window(source_content, 16000)}"
                    f"\n\n{CASE_SCHEMA_PROMPT}"
                ),
            },
        ]
        response = AiService.json_chat(messages, max_tokens=8000)
        patch_payload = extract_ai_json(response)
        existing = generated_payload.get("cases") or []
        seen = {item.get("source_hash") or item.get("source_text") or item.get("title") for item in existing}
        for item in patch_payload.get("cases") or []:
            key = item.get("source_hash") or item.get("source_text") or item.get("title")
            if key and key not in seen:
                existing.append(item)
                seen.add(key)
        generated_payload["cases"] = existing
        generated_payload.setdefault("warnings", []).extend(patch_payload.get("warnings") or [])
        return generated_payload

    @classmethod
    def deep_patch_cases(
        cls,
        *,
        generated_payload: dict,
        source_content: str,
        requirement_context: str,
        user_instruction: str,
        skill: AiSkill | None,
        ai_role: str | None,
        task: AiAgentTask | None = None,
    ) -> dict:
        if task:
            AiTaskService.update_progress(task, 72, "深度补漏", "正在核对遗漏用例")
        case_digest = [
            {
                "case_no": item.get("case_no"),
                "title": item.get("title"),
                "test_point": item.get("test_point"),
                "scenario_type": item.get("scenario_type"),
                "source_text": item.get("source_text"),
            }
            for item in (generated_payload.get("cases") or [])
        ]
        messages = [
            {"role": "system", "content": build_system_prompt(skill, ai_role)},
            {
                "role": "user",
                "content": (
                    "请检查已生成的测试平台功能用例是否遗漏原始用例文档中的明确用例、重要验收点、异常、边界、权限、数据或流程场景。"
                    "只输出需要补充新增的 cases；如果没有遗漏，cases 输出空数组。不要重复输出已生成用例。"
                    f"\n补充要求：{user_instruction}"
                    f"\n已生成用例摘要：{json.dumps(case_digest, ensure_ascii=False)[:50000]}"
                    f"\n需求文档：\n{cls.text_window(requirement_context, 12000)}"
                    f"\n原始用例文档：\n{cls.text_window(source_content, 30000)}"
                    f"\n\n{CASE_SCHEMA_PROMPT}"
                ),
            },
        ]
        response = AiService.json_chat(messages, max_tokens=8000)
        patch_payload = extract_ai_json(response)
        existing = generated_payload.get("cases") or []
        seen = {item.get("source_hash") or item.get("source_text") or item.get("title") for item in existing}
        added_count = 0
        for item in patch_payload.get("cases") or []:
            key = item.get("source_hash") or item.get("source_text") or item.get("title")
            if key and key not in seen:
                existing.append(item)
                seen.add(key)
                added_count += 1
        generated_payload["cases"] = existing
        generated_payload.setdefault("warnings", []).extend(patch_payload.get("warnings") or [])
        generated_payload["deep_patch"] = {"added_count": added_count}
        if task:
            AiTaskService.update_progress(task, 80, "深度补漏", f"补漏完成，新增 {added_count} 条用例")
        return generated_payload
