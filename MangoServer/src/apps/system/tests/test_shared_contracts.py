import json
from pathlib import Path

from django.test import SimpleTestCase
from mangotools.contracts import (
    ActuatorPresenceUpdate,
    ActuatorSystemErrorContract,
    ApiRecordingContract,
    ExecutorTaskClaimContract,
    ExecutorTaskDrainingContract,
    ExecutorTaskHeartbeatContract,
    ExecutorTaskProgressContract,
    ExecutorTaskProgressRequestContract,
    ExecutorTaskResultContract,
    PytestExecutionCommand,
    PytestExecutionResult,
    PytestSourceSnapshotContract,
    SocketCommandContract,
    SocketEnvelopeContract,
    TaskPullRequest,
    TestSuiteDetailResultContract,
    UiAuthStorageItemContract,
    UiCaseExecutionContract,
    UiCaseResultContract,
    UiEnvironmentContract,
    UiFlowRuntimeNodeContract,
    UiPageStepExecutionContract,
    UiPageStepResultContract,
    UiPublicVariableContract,
    UiRecordingCommand,
    UiStepDataContract,
)
from mangotools.enums import TestCaseTypeEnum

from src.apps.auto_api.schemas.recording import ApiRecordingSchema
from src.apps.auto_ui.schemas.execution import UiPageStepExecutionSchema

SNAPSHOT_PATH = Path(__file__).with_name("snapshots") / "shared_contracts.json"
CONTRACTS = (
    ActuatorSystemErrorContract,
    ActuatorPresenceUpdate,
    ApiRecordingContract,
    ExecutorTaskClaimContract,
    ExecutorTaskDrainingContract,
    ExecutorTaskHeartbeatContract,
    ExecutorTaskProgressContract,
    ExecutorTaskProgressRequestContract,
    ExecutorTaskResultContract,
    PytestExecutionCommand,
    PytestExecutionResult,
    PytestSourceSnapshotContract,
    SocketCommandContract,
    SocketEnvelopeContract,
    TaskPullRequest,
    TestSuiteDetailResultContract,
    UiAuthStorageItemContract,
    UiCaseExecutionContract,
    UiCaseResultContract,
    UiEnvironmentContract,
    UiFlowRuntimeNodeContract,
    UiPageStepExecutionContract,
    UiPageStepResultContract,
    UiPublicVariableContract,
    UiRecordingCommand,
    UiStepDataContract,
)


class SharedContractTests(SimpleTestCase):
    def test_json_schema_snapshot(self):
        expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        actual = {contract.__name__: contract.model_json_schema() for contract in CONTRACTS}
        self.assertEqual(expected, actual)

    def test_socket_contract_round_trip(self):
        payload = SocketEnvelopeContract(
            code=200,
            msg="ok",
            user="tester@example.com",
            data=SocketCommandContract(func_name="get_task", func_args=[{"type": 1}]),
        ).model_dump(mode="json")
        restored = SocketEnvelopeContract.model_validate(payload)
        self.assertEqual("get_task", restored.data.func_name)
        self.assertEqual(1, restored.protocol_version)

    def test_task_result_contract_round_trip(self):
        payload = TestSuiteDetailResultContract(
            id=12,
            type=TestCaseTypeEnum.API,
            test_suite=34,
            status=1,
            result_data={"id": 56, "status": 1},
        ).model_dump(mode="json")
        restored = TestSuiteDetailResultContract.model_validate(payload)
        self.assertEqual(TestCaseTypeEnum.API, restored.type)
        self.assertEqual(56, restored.result_data["id"])

    def test_executor_task_contract_round_trip(self):
        claim = ExecutorTaskClaimContract(
            connection_id="connection-1",
            capacity=2,
            supported_task_types=["ui_case"],
        )
        self.assertEqual(2, ExecutorTaskClaimContract.model_validate_json(claim.model_dump_json()).capacity)

        progress = ExecutorTaskProgressRequestContract(
            connection_id="connection-1",
            progress=ExecutorTaskProgressContract(percent=50, current=1, total=2),
        )
        self.assertEqual(50, progress.model_dump(mode="json")["progress"]["percent"])

        result = ExecutorTaskResultContract(success=False, error_code="FAILED", error_message="failed")
        self.assertFalse(ExecutorTaskResultContract.model_validate(result.model_dump()).success)

        system_error = ActuatorSystemErrorContract(
            operation="execute",
            exception_type="RuntimeError",
            message="failed",
        )
        self.assertEqual("execute", system_error.operation)

    def test_legacy_api_recording_adapter(self):
        contract = ApiRecordingContract.model_validate(
            {
                "project_product": 1,
                "username": "tester@example.com",
                "name": "recorded request",
                "url": "https://example.com/api/items",
                "method": 1,
                "json": {"name": "sample"},
            }
        )
        schema = ApiRecordingSchema.from_contract(contract)
        self.assertEqual("json", schema.body_type)
        self.assertEqual({"source_type": "value", "body": {"name": "sample"}}, schema.body_config)

    def test_ui_command_contract_round_trip(self):
        command = UiRecordingCommand(url_list=[{"url": "https://example.com"}])
        restored = UiRecordingCommand.model_validate_json(command.model_dump_json())
        self.assertEqual("https://example.com", restored.url_list[0]["url"])

    def test_ui_page_step_schema_round_trip_through_wire_contract(self):
        schema = UiPageStepExecutionSchema(
            id=7,
            name="open page",
            project_product=3,
            project_product_name="Example Product",
            module_name="Example Module",
            test_env=1,
            type=0,
            url="https://example.com",
            switch_step_open_url=True,
            environment_config=UiEnvironmentContract(id=9, test_object_value="https://example.com"),
        )
        wire = UiPageStepExecutionContract.model_validate(schema.model_dump(mode="json"))
        restored = UiPageStepExecutionSchema.model_validate(wire.model_dump(mode="json"))
        self.assertEqual(schema.id, restored.id)
        self.assertEqual(schema.step_control, restored.step_control)
