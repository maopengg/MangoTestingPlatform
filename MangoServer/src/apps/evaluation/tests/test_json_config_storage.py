from copy import deepcopy
from django.test import SimpleTestCase
from pydantic import ValidationError
from src.apps.evaluation.api.serializers.grade_result import GradeResultSerializer
from src.apps.evaluation.api.serializers.item_result import ItemResultSerializer
from src.apps.evaluation.models import (
    EvaluationDataset,
    EvaluationDatasetVersion,
    EvaluationCase,
    EvaluationItemResult,
    EvaluationGradeResult,
)
from src.apps.evaluation.exceptions import EvaluationError
from src.apps.evaluation.schemas import EvaluationCaseConfig
from src.apps.evaluation.schemas.detail import EvaluationGradeSnapshot, EvaluationItemDetails
from src.apps.evaluation.services.assets.case import EvaluationCaseService
from src.apps.evaluation.services.execution.execution import EvaluationCaseExecutionService
from src.apps.evaluation.services.execution.item_detail import update_item_details
from src.apps.test_center.models import ProjectProduct
from types import SimpleNamespace
from unittest.mock import patch


class JsonConfigurationStorageTests(SimpleTestCase):
    @staticmethod
    def config(answer):
        return {
            "schema_version": 1,
            "target": {"type": "script", "parameters": {"code": 'def main(input, context): return ' + repr({"answer": answer})}},
            "grading": {"default_graders": [{"grader_key": "exact_match", "metric_key": "accuracy"}]},
        }

    def case(self, answer):
        product = ProjectProduct(pk=5)
        dataset = EvaluationDataset(pk=3)
        version = EvaluationDatasetVersion(pk=7, dataset=dataset, status="published")
        return EvaluationCase(pk=1, project_product=product, dataset_version=version, config=self.config(answer))

    def test_json_contract_requires_target_and_scoring_and_rejects_unknown_version(self):
        original = self.config("原值")
        for change in ({"schema_version": 2}, {"extra": True}, {"target": {"type": "static", "ref_id": -1}}, {"target": {"type": "static", "ref_id": 9223372036854775808}}):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                EvaluationCaseConfig.model_validate({**original, **change})
        with self.assertRaises(ValidationError):
            EvaluationCaseConfig.model_validate({"target": original["target"]})
        with self.assertRaises(ValidationError):
            EvaluationCaseConfig.model_validate({"grading": original["grading"]})

    def test_status_only_save_does_not_restore_stale_json_configuration(self):
        stale = self.case("旧值")
        current = self.case("另一位用户已保存的新值")
        with patch.object(EvaluationCaseService, "selected_items", return_value=[]):
            attributes = EvaluationCaseService.normalize({"status": "enabled"}, stale)
        self.assertNotIn("config", attributes)
        frozen_current = deepcopy(current.config)
        with patch.object(EvaluationCaseService, "selected_items", return_value=[]), patch.object(EvaluationCase.objects, "select_for_update") as locked, patch.object(EvaluationCase, "save"):
            locked.return_value.select_related.return_value.get.return_value = current
            result = EvaluationCaseService.save.__wrapped__(EvaluationCaseService, values=attributes, instance=stale)
        self.assertEqual(result.config, frozen_current)
        self.assertEqual(result.status, "enabled")

    def test_detail_updates_preserve_references_zero_timing_and_clear_error(self):
        row = EvaluationItemResult(details={})
        fixture = {"execution_id": 12, "data": {"resource": "R1"}}
        update_item_details(row, references={"fixture": fixture}, timing={"execution_ms": 0})
        fixture["data"]["resource"] = "changed"
        update_item_details(row, references={"oracle": {"trace_id": "trace-1"}}, timing={"grade_ms": 25}, error_message="执行失败")
        update_item_details(row, error_message=None)
        parsed = EvaluationItemDetails.model_validate(row.details)
        self.assertEqual(parsed.references.fixture["data"]["resource"], "R1")
        self.assertEqual(parsed.references.oracle, {"trace_id": "trace-1"})
        self.assertEqual(parsed.timing.execution_ms, 0)
        self.assertEqual(parsed.timing.grade_ms, 25)
        self.assertIsNone(parsed.error_message)

    def test_performance_summary_reads_detail_timing_without_losing_zero(self):
        rows = [
            SimpleNamespace(details={"timing": {"execution_ms": 0, "grade_ms": 0}}, attempts=[{}]),
            SimpleNamespace(details={"timing": {"execution_ms": 20, "grade_ms": 50}}, attempts=[{}, {}]),
            SimpleNamespace(details={}, attempts=[]),
        ]
        result = EvaluationCaseExecutionService._performance_summary(rows)
        self.assertEqual(result["execution_p50_ms"], 0)
        self.assertEqual(result["execution_p95_ms"], 20)
        self.assertEqual(result["grade_p95_ms"], 50)
        self.assertEqual(result["total_attempts"], 3)

    def test_json_detail_and_metric_config_reject_invalid_values(self):
        for payload in ({"schema_version": 2}, {"timing": {"execution_ms": -1}}, {"references": {"unknown": {}}}):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                EvaluationItemDetails.model_validate(payload)
        for payload in ({"schema_version": 2}, {"weight": -1}, {"threshold": 101}, {"weight": float("inf")}, {"threshold": float("nan")}):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                EvaluationGradeSnapshot.model_validate(payload)
        config = EvaluationGradeSnapshot(binding_hash="binding-test", metric="accuracy", threshold=None, weight=0).model_dump(mode="json")
        self.assertEqual(config["weight"], 0)
        self.assertIsNone(config["threshold"])

    def test_results_expose_the_new_json_contract(self):
        sample_fields = ItemResultSerializer().fields
        self.assertIn("details", sample_fields)
        for field in ("oracle_ref", "fixture_ref", "raw_output_ref", "execution_ref", "duration_ms", "grade_duration_ms", "error_message"):
            self.assertNotIn(field, sample_fields)
        metric_fields = GradeResultSerializer().fields
        self.assertIn("grading_snapshot", metric_fields)
        self.assertNotIn("threshold", metric_fields)
        self.assertNotIn("weight", metric_fields)
        self.assertNotIn("metric_key", metric_fields)
        self.assertNotIn("metric_key", {field.name for field in EvaluationGradeResult._meta.fields})

    def test_grade_replacement_locks_parent_and_persists_metric_in_snapshot(self):
        row = EvaluationItemResult(pk=1)
        grades = [EvaluationGradeResult(item_result=row, grader_key="ranking", grader_version=1,
            grading_snapshot=EvaluationGradeSnapshot(binding_hash="ranking-binding", metric=metric).model_dump(mode="json"))
            for metric in ("ranking", "ranking_mrr", "ranking_recall_at_k")]
        with (patch.object(EvaluationItemResult.objects, "select_for_update") as lock,
              patch.object(EvaluationItemResult, "grade_results") as related,
              patch.object(EvaluationGradeResult.objects, "bulk_create") as create):
            EvaluationCaseExecutionService._save_grade_results.__wrapped__(row, grades)
            lock.return_value.get.assert_called_once_with(pk=1)
            related.all.return_value.delete.assert_called_once()
            create.assert_called_once_with(grades)

    def test_duplicate_metric_results_are_rejected_before_replacing_existing_grades(self):
        row = EvaluationItemResult(pk=1)
        grade = EvaluationGradeResult(item_result=row, grader_key="exact_match", grader_version=1,
            grading_snapshot={"metric": "accuracy"})
        with patch.object(EvaluationItemResult.objects, "select_for_update") as lock:
            with self.assertRaises(EvaluationError):
                EvaluationCaseExecutionService._save_grade_results.__wrapped__(row, [grade, grade])
            lock.assert_not_called()
