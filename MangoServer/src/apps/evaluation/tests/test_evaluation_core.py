from unittest.mock import patch
from src.apps.evaluation.schemas.case import EvaluationGraderBinding
from django.test import SimpleTestCase
from pydantic import ValidationError
from src.apps.evaluation.api.serializers.dataset_version import DatasetVersionSerializer
from src.apps.evaluation.api.serializers.dataset_item import DatasetItemSerializer
from src.apps.evaluation.formatters.payload import (
    apply_mapping,
    content_hash,
    mask_sensitive,
    plaintext_secret_paths,
    select_value,
)
from src.apps.evaluation.schemas import EvaluationGradingConfig
from src.apps.evaluation.services.grading.graders import ContainsGrader, EvaluationGraderRegistry, ExactMatchGrader, FieldExtractionGrader, NumericToleranceGrader, RankingGrader, SetMatchGrader
from src.apps.evaluation.services.dataset.importing import EvaluationApiCaseImportService
from src.apps.evaluation.services.execution.execution import EvaluationCaseExecutionService
from types import SimpleNamespace


class EvaluationCoreTests(SimpleTestCase):
    def test_mapping_extracts_values_without_aliases(self):
        source = {"response": {"contracts": [{"id": 1}]}, "meta": {"user": "u1"}}
        self.assertEqual(select_value(source, "$.response.contracts.0.id"), 1)
        self.assertEqual(apply_mapping(source, {"paths": ["$.response.contracts"]}), [{"id": 1}])
        self.assertEqual(apply_mapping(source, {"paths": ["$.response.contracts", "$.meta.user"]}), [[{"id": 1}], "u1"])

    def test_sensitive_values_are_masked_recursively(self):
        self.assertEqual(mask_sensitive({"cache_all": {"v2token": "example-secret"}}), {"cache_all": {"v2token": "***"}})
        value = {"authorization": "Bearer secret", "nested": [{"password": "secret", "question": "ok"}]}
        self.assertEqual(mask_sensitive(value), {"authorization": "***", "nested": [{"password": "***", "question": "ok"}]})
        self.assertEqual(content_hash({"b": 2, "a": 1}), content_hash({"a": 1, "b": 2}))
        self.assertEqual(plaintext_secret_paths({"identity": {"token": "plain"}}), ["identity.token"])
        self.assertEqual(plaintext_secret_paths({"identity": {"token": "${{secret.contract_user}}"}}), [])

    def test_set_match_reports_precision_recall_and_f1(self):
        result = SetMatchGrader.evaluate(
            dataset_item={"expected_output": {"contract_ids": ["C1", "C2"]}},
            actual={"contract_ids": ["C1", "C3"]},
            config={"expected_path": "contract_ids", "actual_path": "contract_ids"},
            metric_key="contract_set_f1", threshold=80,
        )
        metrics = {item.key: item for item in result.metrics}
        self.assertEqual(metrics["contract_set_f1"].score, 50)
        self.assertFalse(metrics["contract_set_f1"].passed)
        self.assertIn('"C2"', metrics["contract_set_f1"].evidence["missing"])

    def test_empty_contract_sets_are_a_correct_match(self):
        result = SetMatchGrader.evaluate(
            dataset_item={"expected_output": {"contract_ids": []}}, actual={"contract_ids": []},
            config={"expected_path": "contract_ids", "actual_path": "contract_ids"},
            metric_key="contract_set_f1", threshold=100,
        )
        self.assertTrue(result.metrics[0].passed)
        self.assertEqual(result.metrics[0].score, 100)

    def test_behavior_and_numeric_rules_are_deterministic(self):
        exact = ExactMatchGrader.evaluate(
            dataset_item={"expected_output": {"behavior": "answer_empty"}}, actual={"behavior": "answer_empty"},
            config={"expected_path": "behavior", "actual_path": "behavior"}, metric_key="behavior", threshold=100,
        )
        numeric = NumericToleranceGrader.evaluate(
            dataset_item={"expected_output": {"count": 10}}, actual={"count": 11},
            config={"expected_path": "count", "actual_path": "count", "absolute_tolerance": 1},
            metric_key="count", threshold=100,
        )
        self.assertTrue(exact.metrics[0].passed)
        self.assertTrue(numeric.metrics[0].passed)

    def test_contains_respects_configured_threshold(self):
        result = ContainsGrader.evaluate(
            dataset_item={"expected_output": {"keywords": ["订单", "编号"]}},
            actual={"text": "订单列表"},
            config={"expected_path": "keywords", "actual_path": "text"},
            metric_key="keywords", threshold=50,
        )
        self.assertTrue(result.metrics[0].passed)

    def test_plan_requires_enabled_weighted_grader(self):
        with self.assertRaises(ValidationError):
            EvaluationGraderBinding.model_validate({"grader_key": "exact_match", "metric_key": "x", "weight": -1})
        config = EvaluationGradingConfig.model_validate({
            "default_graders": [{
                "grader_key": "set_match", "metric_key": "contract_set_f1",
                "weight": 1, "threshold": 100,
            }],
        })
        self.assertEqual(config.aggregation.policy_version, 2)



    def test_version_parent_relations_are_immutable(self):
        self.assertIn("dataset", DatasetVersionSerializer.Meta.read_only_fields)
        self.assertIn("dataset_version", DatasetItemSerializer.Meta.read_only_fields)


    def test_api_case_ground_truth_keys_are_explicit(self):
        self.assertEqual(EvaluationApiCaseImportService._expected_from_variant({"expected": {"ids": [1]}}), ({"ids": [1]}, "expected"))
        self.assertEqual(EvaluationApiCaseImportService._expected_from_variant({"keyword": "订单"}), (None, None))

    def test_builtin_grader_version_must_match(self):
        grader, _config = EvaluationGraderRegistry.resolve("set_match", 1)
        missing, _config = EvaluationGraderRegistry.resolve("set_match", 999)
        self.assertIsNotNone(grader)
        self.assertIsNone(missing)

    def test_group_and_stability_summary(self):
        rows = [
            SimpleNamespace(dataset_item_id="S1", score=90, verdict="passed", item_snapshot={"priority": "P1", "tags": ["有订单"]}),
            SimpleNamespace(dataset_item_id="S1", score=80, verdict="warning", item_snapshot={"priority": "P1", "tags": ["有订单"]}),
            SimpleNamespace(dataset_item_id="S2", score=100, verdict="passed", item_snapshot={"priority": "P2", "tags": ["无订单"]}),
        ]
        groups = EvaluationCaseExecutionService._group_summary(rows)
        stability = EvaluationCaseExecutionService._stability_summary(rows)
        self.assertEqual(groups["tag"]["有订单"]["pass_rate"], 0.5)
        self.assertEqual(stability["repeated_item_count"], 1)
        self.assertEqual(stability["verdict_flip_count"], 1)

    def test_group_gate_can_require_every_bucket_or_one_bucket(self):
        config = EvaluationGradingConfig.model_validate({
            "default_graders": [{"grader_key": "set_match", "metric_key": "set", "weight": 1}],
            "quality_gates": [
                {"key": "pass_rate", "group_by": "tag", "operator": "gte", "threshold": 0.8},
                {"key": "pass_rate", "group_by": "priority:P0", "operator": "gte", "threshold": 1},
            ],
        })
        summary = {
            "groups": {
                "tag": {"normal": {"pass_rate": 1}, "permission": {"pass_rate": 0.75}},
                "priority": {"P0": {"pass_rate": 1}},
            },
        }
        gates = EvaluationCaseExecutionService._evaluate_gates(summary, SimpleNamespace(grading=config))
        self.assertFalse(gates[0]["passed"])
        self.assertTrue(gates[1]["passed"])

    def test_extraction_and_ranking_metrics(self):
        extraction = FieldExtractionGrader.evaluate(
            dataset_item={"expected_output": {"contract": {"id": "C1", "amount": 100}}},
            actual={"contract": {"id": "C1", "amount": 90}},
            config={"expected_path": "contract", "actual_path": "contract"},
            metric_key="fields", threshold=80,
        )
        self.assertEqual(extraction.metrics[0].score, 50)
        self.assertIn("amount", extraction.metrics[0].evidence["incorrect_fields"])
        ranking = RankingGrader.evaluate(
            dataset_item={"expected_output": {"ids": ["C1", "C2"]}},
            actual={"ids": ["C3", "C1", "C2"]},
            config={"expected_path": "ids", "actual_path": "ids", "k": 2},
            metric_key="ranking", threshold=40,
        )
        metrics = {item.key: item for item in ranking.metrics}
        self.assertEqual(metrics["ranking_mrr"].score, 50)
        self.assertEqual(metrics["ranking_recall_at_k"].score, 50)
