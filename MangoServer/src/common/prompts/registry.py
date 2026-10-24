"""提示词显式注册表。新增提示词时必须在这里登记。"""

PROMPT_FILES = {
    "evaluation.judge": "evaluation_judge.yaml",
    "evaluation.memory": "evaluation_memory.yaml",
    "evaluation.memory_scoring": "evaluation_memory_scoring.yaml",
    "evaluation.summary": "evaluation_summary.yaml",
    "data_source.alias": "data_source_alias.yaml",
    "agent.roles": "agent_roles.yaml",
    "ai.assistant": "ai_assistant.yaml",
    "ai.health_check": "ai_health_check.yaml",
    "ai.json_repair": "json_repair.yaml",
    "ai.mcp_service": "mcp_service.yaml",
    "api.automation": "api_automation.yaml",
    "api.assertion_diagnosis": "api_assertion_diagnosis.yaml",
    "api.case_diagnosis": "api_case_diagnosis.yaml",
    "functional.case": "functional_case.yaml",
    "pytest.case_inference": "pytest_case_inference.yaml",
    "report.quality_effectiveness.summary": "quality_effectiveness_summary.yaml",
    "report.quality_effectiveness.insight": "quality_effectiveness_insight.yaml",
    "ui.locator_recommendation": "ui_locator_recommendation.yaml",
}
