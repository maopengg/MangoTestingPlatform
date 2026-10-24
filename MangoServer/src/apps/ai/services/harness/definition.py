# -*- coding: utf-8 -*-
from src.apps.ai.enums.role import AgentRole
from src.apps.ai.models import AiAgentDefinition
from src.apps.ai.services.harness.regression import HarnessRegressionGate
from src.common.prompts import get_prompt

_HARNESS_PROMPTS = get_prompt("agent.roles").values["harness"]

DEFINITIONS = {
    "functional_case": {
        "version": 2,
        "role_key": AgentRole.BUSINESS_TEST_EXPERT.value,
        "allowed_roles": [
            AgentRole.BUSINESS_TEST_EXPERT.value,
            AgentRole.API_AUTOMATION_EXPERT.value,
        ],
        "workflow_schema": {
            "steps": [
                "collect_context",
                "understand_requirement",
                "inventory_existing_cases",
                "analyze_coverage",
                "plan_cases",
                "generate_case_batches",
                "normalize_cases",
                "deduplicate_cases",
                "evaluate_coverage",
                "repair_cases",
                "plan_changes",
                "commit_cases",
                "post_validate",
            ]
        },
        "prompt_template": _HARNESS_PROMPTS["functional_case"],
        "validation_policy": {"schema": True, "deduplicate": True, "coverage": True},
        "budget_policy": {
            "max_model_calls": 20,
            "max_total_tokens": 240000,
            "max_repair_rounds": 2,
            "deadline_seconds": 3600,
        },
    },
    "api_automation": {
        "version": 2,
        "role_key": AgentRole.API_AUTOMATION_EXPERT.value,
        "allowed_roles": [
            AgentRole.API_AUTOMATION_EXPERT.value,
            AgentRole.BUSINESS_TEST_EXPERT.value,
        ],
        "workflow_schema": {
            "steps": [
                "collect_context",
                "load_capabilities",
                "compile_skill",
                "plan_workflow",
                "validate_plan",
                "execute_stages",
                "verify_api_assets",
                "execute_api_case",
                "diagnose_and_repair",
                "bind_result",
                "post_validate",
            ]
        },
        "prompt_template": _HARNESS_PROMPTS["api_automation"],
        "validation_policy": {"api_case_id": True, "assertion": True, "executed_once": True},
        "budget_policy": {
            "max_model_calls": 30,
            "max_total_tokens": 180000,
            "max_mcp_calls": 100,
            "max_replans": 2,
            "deadline_seconds": 3600,
        },
    },
}


class AgentDefinitionService:
    @staticmethod
    def active(agent_key: str) -> AiAgentDefinition:
        payload = dict(DEFINITIONS[agent_key])
        version = payload.pop("version")
        definition = AiAgentDefinition.objects.filter(
            agent_key=agent_key,
            version=version,
            status=1,
        ).first()
        if definition:
            return definition
        regression_report = HarnessRegressionGate.require_passed(agent_key, payload)
        payload["validation_policy"] = {
            **(payload.get("validation_policy") or {}),
            "activation_gate": regression_report,
        }
        return AiAgentDefinition.objects.create(
            agent_key=agent_key,
            version=version,
            status=1,
            **payload,
        )

    @classmethod
    def resolve_role(cls, agent_key: str, requested_role: str | None) -> str:
        definition = cls.active(agent_key)
        allowed_roles = list(definition.allowed_roles or []) or [definition.role_key]
        return AgentRole.normalize(requested_role, definition.role_key, allowed_roles=allowed_roles)
