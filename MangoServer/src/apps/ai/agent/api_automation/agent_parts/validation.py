# -*- coding: utf-8 -*-
from src.apps.ai.agent.api_automation.executor import ApiAutomationExecutor
from src.apps.ai.exceptions import ai_service_error
from src.apps.ai.models import AiAgentTask, AiAgentToolCall
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.functional_test.enums import ManualTestAutomationTypeEnum
from src.apps.functional_test.models import ManualTestCase
from src.apps.functional_test.selectors.querysets import FunctionalTestQuerySelector


class ApiAutomationValidationMixin:
    @staticmethod
    def task_snapshot(task: AiAgentTask) -> dict:
        return {
            "id": task.id,
            "status": task.status,
            "input_data": task.input_data or {},
            "output_data": task.output_data or {},
            "error_message": task.error_message or "",
        }

    @classmethod
    def post_validate_plan(
            cls,
            task: AiAgentTask,
            manual_case: ManualTestCase,
            input_data: dict,
            plan: dict,
            skill_contract: dict,
    ) -> dict:
        api_case_id = plan.get("api_case_id")
        if not api_case_id or not ApiQuerySelector.api_case().filter(id=api_case_id).exists():
            raise ai_service_error("API 自动化写入后未查询到真实 API Case")
        old_id = input_data.get("existing_api_case_id")
        if old_id and int(old_id) != int(api_case_id):
            raise ai_service_error(f"已绑定 API Case 必须覆盖旧 ID：{old_id}")
        assertion_summary = ApiAutomationExecutor.validate_api_case_assertions(int(api_case_id))
        binding = FunctionalTestQuerySelector.manual_test_automation_binding().filter(
            manual_case=manual_case,
            automation_type=ManualTestAutomationTypeEnum.API.value,
            api_case_id=api_case_id,
        ).first()
        if not binding:
            raise ai_service_error("API 自动化写入后未查询到功能用例绑定")
        execution_record_id = plan.get("execution_record_id")
        execution_record = AiAgentToolCall.objects.filter(
            id=execution_record_id,
            task=task,
            tool_name__in=ApiAutomationExecutor.API_RUN_TOOLS,
        ).first()
        if not execution_record:
            raise ai_service_error("API 自动化写入后未查询到本次执行记录")
        skill_assets = cls.validate_required_assets(int(api_case_id), skill_contract)
        return {
            "api_case_id": int(api_case_id),
            "binding_id": binding.id,
            "execution_record_id": execution_record.id,
            "assertion_summary": assertion_summary,
            "old_id_preserved": not old_id or int(old_id) == int(api_case_id),
            "skill_assets": skill_assets,
        }

    @staticmethod
    def validate_required_assets(api_case_id: int, skill_contract: dict) -> dict:
        return ApiAutomationExecutor.validate_required_assets(api_case_id, skill_contract)
