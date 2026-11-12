from genson import SchemaBuilder

from src.apps.auto_api.exceptions import (
    API_VERSION_JSON_SCENARIO_RESPONSE_ASSERTION_GENERATE_INVALID,
    AutoApiError,
)
from src.apps.auto_api.models import ApiCaseDetailedParameter
from src.apps.auto_api.services.api_case.mutation import ApiCaseAggregateMutationService
from src.apps.test_center.services.results.execution_result import ExecutionResultService


class ApiCaseScenarioSchemaService:
    """根据最近一次场景响应生成并保存 Schema 断言。"""

    @classmethod
    def generate(
            cls,
            scenario_id: int,
            *,
            operator_id: int | None = None,
            source: str = "page",
    ) -> dict:
        parameter = ApiCaseDetailedParameter.objects.select_related("case_detailed").get(
            id=scenario_id
        )
        case_id = parameter.case_detailed.case_id
        result_data = ExecutionResultService.latest_api_case_parameter_result(
            case_id=case_id,
            parameter_id=parameter.id,
        )
        response_data = (result_data or {}).get("response") or {}
        if "json" not in response_data:
            raise AutoApiError(API_VERSION_JSON_SCENARIO_RESPONSE_ASSERTION_GENERATE_INVALID)

        builder = SchemaBuilder()
        builder.add_object(response_data["json"])
        schema = builder.to_schema()

        def save_schema(_):
            locked_parameter = ApiCaseDetailedParameter.objects.select_for_update().get(
                id=scenario_id
            )
            locked_parameter.ass_schema = schema
            update_fields = ["ass_schema", "update_time"]
            if operator_id is not None:
                locked_parameter.update_user_id = operator_id
                update_fields.append("update_user")
            locked_parameter.save(update_fields=update_fields)

        ApiCaseAggregateMutationService.mutate(
            case_id,
            action="auto_schema",
            operation=save_schema,
            operator_id=operator_id,
            source=source,
            refresh_case_flow=False,
        )
        return {
            "scenario_id": parameter.id,
            "case_id": case_id,
            "ass_schema": schema,
        }
