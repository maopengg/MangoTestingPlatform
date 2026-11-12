from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase
from pydantic import ValidationError
from src.apps.evaluation.schemas.dataset import EvaluationDatasetSchema
from src.apps.evaluation.schemas.workflow import EvaluationItemScenario, EvaluationWorkflowStep
from src.apps.evaluation.services.targets.target_input import compile_target_input
from src.apps.evaluation.services.workflow.workflow import replace_workflow_values, EvaluationWorkflowRunner
from src.apps.evaluation.exceptions import EvaluationError


class DatasetWorkflowTests(SimpleTestCase):
    def test_multiple_inputs_keep_types_and_never_read_truth(self):
        data = SimpleNamespace(input_data={"question": "哪里", "attachments": ["example.txt"], "flag": False}, expected_output={"answer": "北京"})
        variables = [{"name": "question", "path": "$.question"}, {"name": "attachments", "path": "$.attachments"}, {"name": "flag", "path": "$.flag"}]
        self.assertEqual(compile_target_input(data, input_variables=variables), {"question": "哪里", "attachments": ["example.txt"], "flag": False})
        for value in (0, False, [], "", {}):
            self.assertEqual(compile_target_input(SimpleNamespace(input_data=value), input_variables=[{"name": "case_input", "path": "$"}]), {"case_input": value})

    def test_variables_are_unique_and_reserved_names_rejected(self):
        for variables in ([{"name": "steps"}], [{"name": "q"}, {"name": "q"}], []):
            with self.assertRaises(ValidationError):
                EvaluationDatasetSchema(input_variables=variables)

    def test_turn_schemas_validate_turn_data_instead_of_unused_parent_input(self):
        from src.apps.evaluation.services.dataset.versioning import EvaluationVersionService
        version = SimpleNamespace(schema_snapshot={"input_schema": {"type": "object", "required": ["question"]},
            "workflow": {"sequence": "conversation"}})
        sample = {"input_data": {}, "expected_output": {}, "priority": "P1", "scenario": {
            "turns": [{"input_data": {"question": "哪里"}, "expected_output": {"answer": "北京"}}]}}
        EvaluationVersionService.validate_item(version, sample)
        sample["scenario"]["turns"][0]["input_data"] = {}
        with self.assertRaises(EvaluationError):
            EvaluationVersionService.validate_item(version, sample)

    def test_nested_runtime_references_keep_types_and_cycles_are_rejected(self):
        self.assertEqual(replace_workflow_values("${{turn.input}}", {"turn": {"input": {"id": "${{steps.read.id}}"}}, "steps": {"read": {"id": 7}}}), {"id": 7})
        with self.assertRaises(EvaluationError):
            replace_workflow_values("${{a}}", {"a": "${{b}}", "b": "${{a}}"})

    def test_reference_preserves_typed_values_and_fails_missing(self):
        self.assertEqual(replace_workflow_values({"ids": "${{steps.prepare.ids}}", "name": "run-${{session.id}}"},
            {"steps": {"prepare": {"ids": [1, 2]}}, "session": {"id": "abc"}}), {"ids": [1, 2], "name": "run-abc"})
        with self.assertRaises(EvaluationError):
            replace_workflow_values("${{steps.missing}}", {"steps": {}})

    def test_material_is_not_a_scored_question_and_ready_requires_condition(self):
        with self.assertRaises(ValidationError):
            EvaluationItemScenario(turns=[{"kind": "material", "score": True}])
        with self.assertRaises(ValidationError):
            EvaluationWorkflowStep(id="ready", name="等待", stage="ready", action="script", code="def main(input, context): return {}")

    def runner(self, steps):
        config = EvaluationDatasetSchema(workflow={"preparation": "create", "steps": steps})
        execution = SimpleNamespace(id=1, details={}, save=lambda **kwargs: None)
        runner = EvaluationWorkflowRunner(execution, SimpleNamespace(dataset_config=config))
        runner.stopped = lambda: False
        return runner

    def test_failed_prepare_always_cleans_and_never_runs_target(self):
        runner = self.runner([
            {"id": "create", "name": "准备", "scope": "execution", "action": "script", "code": "def main(input, context): return {}"},
            {"id": "clean", "name": "清理", "scope": "execution", "stage": "cleanup", "action": "script", "code": "def main(input, context): return {}"},
        ])
        calls = []
        def call(step, *args):
            calls.append(step.id)
            if step.id == "create":
                from src.apps.evaluation.services.assets.validation import invalid_config
                raise invalid_config("准备失败")
            return {"cleaned": True}
        runner.call = call
        with self.assertRaises(Exception):
            with runner.execution_scope():
                self.fail("Failed preparation reached the target")
        self.assertEqual(calls, ["create", "clean"])
        self.assertEqual(runner.records[-1]["status"], "success")

    def test_dynamic_gold_is_not_added_to_target_variables(self):
        runner = self.runner([{"id": "gold", "name": "参考", "stage": "reference", "action": "script", "code": "def main(input, context): return {}"}])
        runner.call = lambda *args: {"expected_output": {"answer": "北京"}, "context": {"source_evidence": ["迁居北京"]}}
        from src.apps.evaluation.enums.workflow import EvaluationWorkflowStageEnum, EvaluationWorkflowScopeEnum
        state = runner.new_state()
        sample = SimpleNamespace(input_data="哪里", expected_output={}, context={})
        runner.run_stage(EvaluationWorkflowStageEnum.REFERENCE, EvaluationWorkflowScopeEnum.ITEM, state, sample)
        sample.runtime_context = state
        self.assertEqual(sample.expected_output, {"answer": "北京"})
        self.assertNotIn("gold", compile_target_input(sample)["steps"])
        self.assertNotIn("expected_output", compile_target_input(sample))

    def test_polling_checks_explicit_failure_without_waiting(self):
        runner = self.runner([{"id": "ready", "name": "等待", "stage": "ready", "action": "script", "code": "def main(input, context): return {}", "until_path": "$.ready", "failure_path": "$.failed"}])
        runner.call = lambda *args: {"ready": False, "failed": True}
        from src.apps.evaluation.enums.workflow import EvaluationWorkflowStageEnum, EvaluationWorkflowScopeEnum
        with self.assertRaises(EvaluationError):
            runner.run_stage(EvaluationWorkflowStageEnum.READY, EvaluationWorkflowScopeEnum.ITEM, runner.new_state())
        self.assertEqual(runner.records[0]["status"], "failed")

    def test_wait_condition_does_not_confuse_boolean_and_number(self):
        self.assertFalse(EvaluationWorkflowRunner.matches({"status": 1}, "$.status", True))
        self.assertFalse(EvaluationWorkflowRunner.matches({}, "$.failed", True))
        self.assertTrue(EvaluationWorkflowRunner.matches({"status": "complete"}, "$.status", "complete"))

    def test_each_group_gets_its_own_session_and_only_one_prepare(self):
        runner = self.runner([{"id": "prepare", "name": "准备", "scope": "group", "action": "script", "code": "def main(input, context): return {}"}])
        calls = []
        runner.call = lambda step, arguments, state, timeout: calls.append(state["session"]["id"]) or {"ready": True}
        sample = SimpleNamespace(input_data={}, expected_output={}, context={})
        with runner.execution_scope():
            for group in ("A", "A", "B"):
                row = SimpleNamespace(item_snapshot={"scenario": {"group_key": group}}, dataset_item_id=group, repeat_index=1)
                with runner.item_scope(row, sample):
                    pass
        self.assertEqual(len(calls), 2)
        self.assertNotEqual(calls[0], calls[1])

    def test_list_processing_is_ordered_and_records_completed_values(self):
        runner = self.runner([{"id": "write", "name": "逐条写入", "action": "script", "code": "def main(input, context): return {}", "input_data": {"materials": ["旧事实", "新事实"]}, "iterate_path": "$.materials"}])
        calls = []
        runner.call = lambda step, arguments, state, timeout: calls.append(arguments["item"]) or {"id": len(calls)}
        from src.apps.evaluation.enums.workflow import EvaluationWorkflowStageEnum, EvaluationWorkflowScopeEnum
        state = runner.new_state()
        runner.run_stage(EvaluationWorkflowStageEnum.PREPARE, EvaluationWorkflowScopeEnum.ITEM, state)
        self.assertEqual(calls, ["旧事实", "新事实"])
        self.assertEqual(state["steps"]["write"], [{"id": 1}, {"id": 2}])
