from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from pydantic import ValidationError

from src.apps.auto_ui.schemas.agent_execution import (
    AgentUiCompletionReport,
    AgentUiRuntimeOperationRequest,
    AgentUiStepReport,
)
from src.apps.auto_ui.services.agent_execution import AgentUiExecutionService
from src.apps.auto_ui.services.agent_runtime import AgentUiRuntimeOperationService
from src.interfaces.mcp.authentication import _domain, _operation, component_policy
from src.interfaces.mcp.server import _tool_operation
from src.interfaces.mcp.tools.ui.agent_execution import register_agent_ui_execution_tools


class _McpRecorder:
    def __init__(self):
        self.names = []

    def tool(self):
        def decorator(func):
            self.names.append(func.__name__)
            return func

        return decorator


class AgentUiExecutionProtocolTests(SimpleTestCase):
    def test_protocol_is_stateless_and_uses_neutral_prefix(self):
        mcp = _McpRecorder()

        register_agent_ui_execution_tools(mcp)

        self.assertEqual(
            mcp.names,
            [
                "agent_ui_get_case",
                "agent_ui_create_execution",
                "agent_ui_execute_runtime",
                "agent_ui_upload_artifact",
                "agent_ui_report_step",
                "agent_ui_complete_execution",
            ],
        )
        self.assertTrue(all(name.startswith("agent_ui_") for name in mcp.names))
        self.assertNotIn("agent_ui_heartbeat_run", mcp.names)
        self.assertNotIn("agent_ui_get_run_status", mcp.names)

    def test_agent_tools_use_ui_case_permissions(self):
        self.assertEqual(_domain("agent_ui_get_case"), ("ui_case", True))
        self.assertEqual(_operation("agent_ui_get_case"), "base")
        self.assertEqual(_operation("agent_ui_report_step"), "execute")
        self.assertEqual(_operation("agent_ui_execute_runtime"), "execute")
        self.assertEqual(_tool_operation("agent_ui_get_case"), "read")
        self.assertEqual(_tool_operation("agent_ui_execute_runtime"), "execute")
        self.assertEqual(_tool_operation("agent_ui_report_step"), "execute")
        self.assertEqual(component_policy("agent_ui_execute_runtime").permission_key, "ui.case:change")
        self.assertEqual(component_policy("agent_ui_report_step").permission_key, "ui.case:change")

    def test_runtime_operation_contract_rejects_unknown_fields(self):
        with self.assertRaises(ValidationError):
            AgentUiRuntimeOperationRequest.model_validate({
                "operation": "prepare_case",
                "idempotency_key": "prepare-0001",
                "unexpected": True,
            })

    def test_runtime_node_operation_accepts_node_reference(self):
        value = AgentUiRuntimeOperationRequest.model_validate({
            "operation": "execute_node",
            "idempotency_key": "node-00000001",
            "step_index": 1,
            "node_id": 221,
            "runtime_variables": {"模版名称": "example"},
        })

        self.assertEqual(value.node_id, 221)
        self.assertEqual(value.runtime_variables["模版名称"], "example")

    def test_runtime_operation_does_not_accept_client_variable_binding_mode(self):
        with self.assertRaises(ValidationError):
            AgentUiRuntimeOperationRequest.model_validate({
                "operation": "bind_outputs",
                "idempotency_key": "binding-0001",
            })

    def test_runtime_operation_limits_context_size(self):
        with self.assertRaises(ValidationError):
            AgentUiRuntimeOperationRequest.model_validate({
                "operation": "prepare_case",
                "idempotency_key": "prepare-0002",
                "runtime_variables": {str(index): index for index in range(10_001)},
            })

    def test_runtime_custom_node_is_returned_for_local_skill_context(self):
        token_data = {
            "execution_id": "exec-1",
            "test_env": 3,
            "steps": [{
                "case_step_id": 10,
                "page_step_id": 20,
                "config_version": 1,
                "is_auth_step": False,
            }],
        }
        node = {
            "id": 30,
            "type": 3,
            "custom": [{"key": "后续名称", "value": "${{模版名称}}-已发布"}],
        }
        with (
            patch.object(
                AgentUiExecutionService,
                "_execution_context",
                return_value=(token_data, SimpleNamespace()),
            ),
            patch.object(AgentUiExecutionService, "_validate_step_version"),
            patch.object(
                AgentUiRuntimeOperationService,
                "_runtime_node",
                return_value=(node, [31]),
            ),
            patch("src.apps.auto_ui.services.agent_runtime.cache.get", return_value=None),
            patch("src.apps.auto_ui.services.agent_runtime.cache.set"),
        ):
            result = AgentUiRuntimeOperationService.execute(
                execution_token="signed",
                project_product_id=1,
                user_id=2,
                username="tester",
                request={
                    "operation": "execute_node",
                    "idempotency_key": "node-custom-0001",
                    "step_index": 0,
                    "node_id": 30,
                    "runtime_variables": {"模版名称": "abc123"},
                },
            )

        self.assertEqual(result["execution_mode"], "agent_context")
        self.assertEqual(result["resolved_custom"][0]["value"], "abc123-已发布")
        self.assertEqual(result["next_node_ids"], [31])

    def test_data_source_cache_record_uses_first_row(self):
        value = AgentUiRuntimeOperationService._cache_record(
            "user_id,user_name",
            {"rows": [{"id": 7, "name": "example"}]},
        )

        self.assertEqual(value, {"id": 7, "name": "example"})

    def test_step_report_rejects_unknown_fields(self):
        with self.assertRaises(ValidationError):
            AgentUiStepReport.model_validate({
                "idempotency_key": "step-0001",
                "status": "passed",
                "summary": "通过",
                "unexpected": True,
            })

    def test_passed_completion_accepts_structured_steps(self):
        result = AgentUiCompletionReport.model_validate({
            "status": "passed",
            "summary": "完成",
            "steps": [{
                "step_index": 0,
                "report": {
                    "idempotency_key": "step-0001",
                    "status": "passed",
                    "summary": "通过",
                },
            }],
        })

        self.assertEqual(result.steps[0].step_index, 0)

    def test_sensitive_result_fields_are_masked(self):
        value = AgentUiExecutionService._sanitize_value({
            "summary": "完成",
            "authorization": "Bearer secret",
            "nested": {"api_key": "secret", "actual": "visible"},
        })

        self.assertEqual(value["authorization"], "***")
        self.assertEqual(value["nested"]["api_key"], "***")
        self.assertEqual(value["nested"]["actual"], "visible")

    def test_artifact_file_name_is_normalized(self):
        self.assertEqual(
            AgentUiExecutionService._safe_file_name("../../失败 截图.png"),
            "失败_截图.png",
        )
