# -*- coding: utf-8 -*-

from src.apps.ai.exceptions import ai_service_error


class HarnessRegressionGate:
    """Deterministic activation checks for versioned Agent definitions."""

    FIXTURES = {
        "functional_case": {
            "required_steps": [
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
            ],
            "required_validation": ["schema", "deduplicate", "coverage"],
            "required_budget": ["max_model_calls", "max_total_tokens", "max_repair_rounds", "deadline_seconds"],
        },
        "api_automation": {
            "required_steps": [
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
            ],
            "required_validation": ["api_case_id", "assertion", "executed_once"],
            "required_budget": ["max_model_calls", "max_total_tokens", "max_mcp_calls", "max_replans",
                                "deadline_seconds"],
        },
    }

    @classmethod
    def evaluate(cls, agent_key: str, definition: dict) -> dict:
        fixture = cls.FIXTURES.get(agent_key)
        if not fixture:
            return {"passed": False, "findings": [f"没有 Agent {agent_key} 的固定回归集"]}

        findings = []
        steps = list((definition.get("workflow_schema") or {}).get("steps") or [])
        if steps != fixture["required_steps"]:
            findings.append("工作流阶段、顺序或数量与固定回归集不一致")
        if len(steps) != len(set(steps)):
            findings.append("工作流包含重复阶段")

        validation = definition.get("validation_policy") or {}
        for key in fixture["required_validation"]:
            if validation.get(key) is not True:
                findings.append(f"缺少启用的校验策略：{key}")

        budget = definition.get("budget_policy") or {}
        for key in fixture["required_budget"]:
            try:
                valid = int(budget.get(key) or 0) > 0
            except (TypeError, ValueError):
                valid = False
            if not valid:
                findings.append(f"运行预算无效：{key}")

        role_key = str(definition.get("role_key") or "").strip()
        allowed_roles = list(definition.get("allowed_roles") or [])
        if not role_key or role_key not in allowed_roles:
            findings.append("默认角色未包含在允许角色中")
        if not str(definition.get("prompt_template") or "").strip():
            findings.append("系统提示词不能为空")

        return {
            "passed": not findings,
            "fixture": agent_key,
            "checked_steps": len(steps),
            "findings": findings,
        }

    @classmethod
    def require_passed(cls, agent_key: str, definition: dict) -> dict:
        report = cls.evaluate(agent_key, definition)
        if not report["passed"]:
            raise ai_service_error(
                f"Agent Harness 版本未通过固定回归门禁：{'；'.join(report['findings'])}"
            )
        return report
