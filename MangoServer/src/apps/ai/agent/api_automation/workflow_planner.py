# -*- coding: utf-8 -*-
import json

from src.apps.ai.agent.api_automation.tool_catalog import ApiAutomationToolStageCatalog
from src.apps.ai.agent.roles import AgentRole
from src.apps.ai.models import AiSkill
from src.apps.ai.service.core import extract_ai_json
from src.apps.functional_test.models import ManualTestCase, ManualTestSuite
from src.apps.system.service.ai.client import AiService


class ApiAutomationWorkflowPlanner:
    @classmethod
    def plan(
        cls,
        *,
        manual_case: ManualTestCase,
        suite: ManualTestSuite,
        skill: AiSkill,
        context_package: dict,
        existing_api_case_id: int | None,
        tool_catalog: list[dict],
        user_instruction: str,
        ai_role: str | None = None,
    ) -> dict:
        payload = {
            "task": "只规划 API 自动化 MCP 工具链，不要调用工具，不要创建或更新任何数据。",
            "suite": {
                "id": suite.id,
                "requirement_name": suite.requirement_name,
                "project_product_id": suite.project_product_id,
                "module_id": suite.module_id,
                "owner_id": suite.owner_id,
            },
            "manual_case": {
                "id": manual_case.id,
                "case_no": manual_case.case_no,
                "project_product_id": manual_case.project_product_id,
                "module_id": manual_case.module_id,
                "title": manual_case.title,
                "test_point": manual_case.test_point,
                "test_data": manual_case.test_data,
                "precondition": manual_case.precondition,
                "test_types": manual_case.test_types,
            },
            "existing_api_case_id": existing_api_case_id,
            "context_summary": context_package.get("context_summary"),
            "reuse_context": context_package.get("reuse_context"),
            "available_stages": tool_catalog,
            "user_instruction": user_instruction,
            "skill": {
                "id": skill.id,
                "name": skill.name,
                "content": skill.content,
            },
            "response_schema": {
                "summary": "string",
                "stages": [
                    {
                        "stage": "resolve_context | ensure_api_info | configure_headers | create_or_update_case | configure_data_factory | add_assertions | add_extractors | execute_and_diagnose",
                        "reason": "为什么需要这个阶段",
                        "tool_names": ["只填写该阶段需要使用的真实 MCP 工具名"],
                    }
                ],
            },
        }
        messages = [
            {
                "role": "system",
                "content": "\n".join(
                    [
                        AgentRole.prompt(ai_role, AgentRole.API_AUTOMATION_EXPERT),
                        "你现在只负责规划工具链。必须输出 JSON 对象，不允许输出 Markdown。",
                        "必须优先按 Skill 的流程安排阶段。已有 API Case 时必须规划为覆盖旧 ID，不允许新建重复 Case。",
                        "平台最低要求：最终必须得到 api_case_id/case_id，并且必须执行一次 API Case。",
                    ]
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        response = AiService.json_chat(messages, temperature=0, max_tokens=2500)
        raw_plan = extract_ai_json(response)
        return ApiAutomationToolStageCatalog.normalize_plan(raw_plan, skill.content or "")
