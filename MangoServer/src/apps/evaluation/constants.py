from src.apps.evaluation.enums import EvaluationTargetTypeEnum


TARGET_EXECUTION_PERMISSIONS = {
    EvaluationTargetTypeEnum.API_CASE.value: "api.case:execute",
    EvaluationTargetTypeEnum.API_INFO.value: "api.info:execute",
    EvaluationTargetTypeEnum.MCP_TOOL.value: "ai.mcp:debug",
}
MCP_EVALUATION_PERMISSIONS = {
    "get_evaluation_schema": "evaluation.case",
    "list_evaluation_ai_profiles": "evaluation.case:detail",
    "create_evaluation_dataset": "evaluation.dataset:create",
    "list_evaluation_datasets": "evaluation.dataset",
    "list_evaluation_dataset_versions": "evaluation.dataset:detail",
    "list_evaluation_dataset_items": "evaluation.dataset:detail",
    "get_evaluation_dataset_quality": "evaluation.dataset:detail",
    "create_evaluation_dataset_version": "evaluation.dataset:edit",
    "update_evaluation_dataset_version": "evaluation.dataset:edit",
    "update_evaluation_dataset_item": "evaluation.dataset:edit",
    "create_evaluation_dataset_item": "evaluation.dataset:edit",
    "delete_evaluation_dataset_version": "evaluation.dataset:delete",
    "list_evaluation_workflow_resources": "evaluation.dataset:detail",
    "publish_evaluation_dataset_version": "evaluation.dataset:publish",
    "list_evaluation_graders": "evaluation.grader",
    "list_evaluation_cases": "evaluation.case",
    "get_evaluation_case": "evaluation.case:detail",
    "create_evaluation_case": "evaluation.case:create",
    "update_evaluation_case": "evaluation.case:edit",
    "update_evaluation_case_status": "evaluation.case:status",
    "run_evaluation_case": "evaluation.case:execute",
    "list_evaluation_case_executions": "evaluation.case:detail",
    "get_evaluation_case_execution": "evaluation.case:detail",
    "list_evaluation_item_results": "evaluation.case:detail",
    "stop_evaluation_case_execution": "evaluation.case:stop",
    "retry_evaluation_case_execution": "evaluation.case:execute",
}
