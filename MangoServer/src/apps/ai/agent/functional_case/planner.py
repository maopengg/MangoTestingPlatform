# -*- coding: utf-8 -*-
from src.apps.ai.agent.functional_case.schema import build_system_prompt
from src.apps.ai.models import AiAgentTask, AiSkill
from src.apps.ai.service.core import AiTaskService, extract_ai_json
from src.apps.system.service.ai.client import AiService


class FunctionalCaseOutlinePlanner:
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
                "content": (
                    "请先不要输出完整用例，只输出场景大纲和预计用例清单。"
                    "输出 JSON：{suite:{}, outline:[{group_name, expected_case_count, case_titles:[...]}], warnings:[]}。\n"
                    f"补充要求：{user_instruction}\n"
                    f"需求文档：\n{cls.text_window(requirement_context, 8000)}\n"
                    f"原始用例/需求资料：\n{cls.text_window(source_content, 24000)}"
                ),
            },
        ]
        response = AiService.json_chat(messages, max_tokens=6000)
        payload = extract_ai_json(response)
        outline = payload.get("outline") if isinstance(payload, dict) else []
        if not isinstance(outline, list) or not outline:
            outline = [{"group_name": "默认场景", "expected_case_count": 0, "case_titles": []}]
        return {"suite": payload.get("suite") or {}, "outline": outline, "warnings": payload.get("warnings") or []}
