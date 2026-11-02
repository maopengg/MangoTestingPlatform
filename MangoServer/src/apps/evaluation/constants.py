from src.apps.evaluation.enums import EvaluationTargetTypeEnum


TARGET_EXECUTION_PERMISSIONS = {
    EvaluationTargetTypeEnum.API_CASE.value: "api.case:read",
    EvaluationTargetTypeEnum.API_INFO.value: "api.info:read",
    EvaluationTargetTypeEnum.MCP_TOOL.value: "api.info:read",
}
