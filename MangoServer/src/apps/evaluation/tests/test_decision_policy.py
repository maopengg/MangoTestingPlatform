from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from src.apps.evaluation.models import EvaluationItemResult
from src.apps.evaluation.schemas import EvaluationGradingConfig, GraderMetric, GraderResult
from src.apps.evaluation.schemas.case import EvaluationCaseConfig, EvaluationGraderBinding
from src.apps.evaluation.services.execution.execution import EvaluationCaseExecutionService as Executions
from src.apps.evaluation.tests.test_case_flow import case_config


class DecisionPolicyTests(SimpleTestCase):
    def aggregate(self, rows, *, valid_rate=1, pass_rate=0.8, hard_failures=0, gates=()):
        execution = SimpleNamespace(item_results=MagicMock(), save=MagicMock())
        execution.item_results.all.return_value = rows
        config = SimpleNamespace(summary_model=None, grader_bindings={}, grading=EvaluationGradingConfig(
            aggregation={"min_valid_rate": valid_rate, "min_effect_pass_rate": pass_rate}, quality_gates=list(gates)))
        with ExitStack() as stack:
            for name in ("_metric_summary", "_classification_summary", "_performance_summary", "_stability_summary"):
                stack.enter_context(patch.object(Executions, name, return_value={}))
            query = stack.enter_context(patch("src.apps.evaluation.services.execution.execution.EvaluationGradeResult.objects.filter"))
            query.return_value.values.return_value.distinct.return_value.count.return_value = hard_failures
            stack.enter_context(patch("src.apps.evaluation.services.reporting.report.sync_report"))
            return Executions.aggregate(execution, config)

    @staticmethod
    def row(key, passed=True, valid=True):
        return SimpleNamespace(dataset_item_id=key, grade_status="graded" if valid else "invalid", verdict="passed" if passed else "failed",
            score=100 if passed else 0, item_snapshot={"weight": 1}, details={})

    def test_one_ordinary_failure_does_not_override_eighty_percent_requirement(self):
        rows = [self.row(str(index), passed=index < 8) for index in range(10)]
        result = self.aggregate(rows)
        self.assertEqual(result.verdict, "passed")
        self.assertEqual(result.summary["effect_pass_rate"], 0.8)
        self.assertEqual(self.aggregate(rows, pass_rate=0.81).verdict, "failed")

    def test_unreliable_coverage_is_invalid_instead_of_a_capability_failure(self):
        result = self.aggregate([self.row("A"), self.row("B", valid=False)])
        self.assertEqual(result.verdict, "invalid")
        self.assertEqual(result.summary["valid_rate"], 0.5)
        self.assertEqual(result.summary["effect_pass_rate"], 1)
        self.assertEqual(self.aggregate([self.row("A", valid=False)]).verdict, "invalid")

    def test_repeated_outcomes_are_counted_instead_of_replaced_by_worst_result(self):
        result = self.aggregate([self.row("A"), self.row("A", passed=False)], pass_rate=0.5)
        self.assertEqual(result.verdict, "passed")
        self.assertEqual(result.summary["item_count"], 1)
        self.assertEqual(result.summary["total"], 2)
        self.assertEqual(result.summary["average_score"], 50)
        self.assertEqual(result.summary["effect_pass_rate"], 0.5)

    def test_explicit_critical_and_warning_gates_override_summary_pass(self):
        rows = [self.row("A")]
        self.assertEqual(self.aggregate(rows, hard_failures=1).verdict, "failed")
        for severity, verdict in (("critical", "failed"), ("warning", "warning")):
            result = self.aggregate(rows, gates=[{"key": "average_score", "operator": "gt", "threshold": 100, "severity": severity}])
            self.assertEqual(result.verdict, verdict)

    def test_new_case_discards_duplicate_legacy_thresholds_without_mutating_source(self):
        old = case_config()
        old["grading"]["aggregation"] = {"pass_score": 100, "warning_score": 70, "invalid_policy": "failed", "min_effect_pass_rate": 0.9}
        config = EvaluationCaseConfig.model_validate(old)
        self.assertEqual(config.grading.aggregation.model_dump(), {"policy_version": 2, "min_valid_rate": 0.95, "min_effect_pass_rate": 0.9})
        self.assertIn("pass_score", old["grading"]["aggregation"])

    def test_failed_assertion_cannot_be_hidden_by_a_high_weighted_score(self):
        row = EvaluationItemResult(pk=1, item_snapshot={"effective_graders": [{"binding_hash": "one"}, {"binding_hash": "two"}]})
        grader = MagicMock()
        grader.evaluate.side_effect = [
            GraderResult(metrics=[GraderMetric(key="one", score=100, passed=True)]),
            GraderResult(metrics=[GraderMetric(key="two", score=90, passed=False)]),
        ]
        config = SimpleNamespace(execution=SimpleNamespace(retry_count=0, item_timeout_seconds=60), grading=EvaluationGradingConfig(),
            grader_bindings={key: EvaluationGraderBinding(grader_key="exact_match", metric_key=key, weight=100 if key == "one" else 1) for key in ("one", "two")})
        adapter = MagicMock()
        adapter.execute.return_value = {"output": "answer"}
        with ExitStack() as stack:
            stack.enter_context(patch.object(EvaluationItemResult, "save"))
            stack.enter_context(patch.object(EvaluationItemResult, "grade_results", MagicMock()))
            stack.enter_context(patch("src.apps.evaluation.services.execution.execution.EvaluationAttemptService.start", return_value=1))
            stack.enter_context(patch("src.apps.evaluation.services.execution.execution.EvaluationAttemptService.finish"))
            stack.enter_context(patch.object(Executions, "_save_grade_results"))
            stack.enter_context(patch("src.apps.evaluation.services.execution.execution.EvaluationGraderRegistry.resolve", return_value=(grader, {})))
            stack.enter_context(patch("src.apps.evaluation.services.execution.execution.EvaluationGraderRegistry.validate_result"))
            Executions._execute_item_core(SimpleNamespace(created_by_id=1), row, config, adapter, SimpleNamespace(executor_config={}), SimpleNamespace(), SimpleNamespace())
        self.assertGreater(float(row.score), 99)
        self.assertEqual(row.verdict, "failed")
