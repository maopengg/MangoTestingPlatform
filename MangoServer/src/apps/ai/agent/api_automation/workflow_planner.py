# -*- coding: utf-8 -*-
import json

from src.apps.ai.agent.api_automation.tool_catalog import ApiAutomationToolStageCatalog
from src.apps.ai.enums.role import AgentRole
from src.apps.ai.model_gateway.client import AgentModelGateway
from src.apps.ai.models import AiAgentTask, AiSkill
from src.apps.ai.services.core import extract_ai_json
from src.apps.functional_test.models import ManualTestCase, ManualTestSuite
from src.common.prompts import get_prompt


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
            skill_contract: dict | None = None,
            task: AiAgentTask | None = None,
    ) -> dict:
        prompt = get_prompt("api.automation")
        payload = {
            "task": prompt.values["workflow_planner_task"],
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
            "skill_contract": skill_contract or {},
            "response_schema": prompt.values["workflow_response_schema"],
        }
        messages = [
            {
                "role": "system",
                "content": prompt.render(
                    "workflow_planner_system",
                    role_prompt=AgentRole.prompt(ai_role, AgentRole.API_AUTOMATION_EXPERT),
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        response = AgentModelGateway.json_chat(
            task=task,
            messages=messages,
            temperature=0,
            max_tokens=2500,
        )
        raw_plan = extract_ai_json(response, task=task)
        return ApiAutomationToolStageCatalog.normalize_plan(
            raw_plan,
            skill.content or "",
            (skill_contract or {}).get("required_capabilities") or [],
            (skill_contract or {}).get("forbidden_capabilities") or [],
        )
