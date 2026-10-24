from copy import deepcopy
from unittest.mock import patch
from django.test import SimpleTestCase
from src.apps.evaluation.exceptions import EvaluationError
from src.apps.evaluation.schemas.case import EvaluationGraderBinding
from src.apps.evaluation.services.grading import validate_bindings
from src.apps.evaluation.services.graders import EvaluationGraderRegistry, MemoryExtractionGrader, MemoryUpdateGrader, MemoryQAGrader


class MemoryScoringTests(SimpleTestCase):
    source = "Alice lived in Shanghai in January. Alice moved to Beijing in February."

    def check(self, index=0, status="supported", quote="Alice now lives in Beijing"):
        return {"index": index, "status": status, "actual_quote": quote,
                "source_quote": self.source, "reason": "主体与时间事实核对"}

    def judgment(self, expected=None, actual=None, **kwargs):
        return {"expected_checks": expected if expected is not None else [self.check()],
                "actual_checks": actual if actual is not None else [self.check()],
                "requires_review": False, "confidence": 0.95, "reason": "核对原文事实", **kwargs}

    def evaluate(self, grader, gold, judgment, actual=None, **kwargs):
        sample = {"input_data": {"query": "Where does Alice live now?"}, "expected_output": gold,
                  "context": {"source_evidence": [{"excerpt": self.source}]}}
        with patch("src.apps.evaluation.services.memory_grading.json_chat", return_value={"choices": [{"message": {"content": judgment}}]}) as chat:
            result = grader.evaluate(dataset_item=sample, actual=actual if actual is not None else ["Alice now lives in Beijing"],
                config={}, metric_key="memory", threshold=kwargs.pop("threshold", 100), **kwargs)
        self.assertEqual(chat.call_args.kwargs["prompt_id"], "evaluation.memory_scoring")
        return result

    def test_three_graders_registered_as_model_and_cannot_be_hard_gates(self):
        catalog = {item["grader_key"]: item for item in EvaluationGraderRegistry.catalog()}
        for key in ("memory_qa", "memory_extraction", "memory_update"):
            self.assertEqual(catalog[key]["category"], "model")
            self.assertEqual(EvaluationGraderRegistry.prompt_id(key), "evaluation.memory_scoring")
            with self.assertRaises(EvaluationError):
                validate_bindings([EvaluationGraderBinding(grader_key=key, grader_version=catalog[key]["grader_version"], metric_key="memory", hard_gate=True)])

    def test_extraction_semantic_coverage_and_precision_are_separate(self):
        # Two expected facts, one omitted; two extracted facts, one unsupported.
        judgment = self.judgment(expected=[self.check(), self.check(1, "omitted", "")],
            actual=[self.check(), self.check(1, "unsupported", "Alice is a doctor")])
        result = self.evaluate(MemoryExtractionGrader, {"memories": ["Alice lives in Beijing", "Alice moved in February"]},
            judgment, ["Alice now lives in Beijing", "Alice is a doctor"])
        self.assertEqual([metric.score for metric in result.metrics], [50, 50, 50])

    def test_partial_extraction_gets_half_credit(self):
        result = self.evaluate(MemoryExtractionGrader, {"memories": ["Alice lives in Beijing since February"]},
            self.judgment(expected=[self.check(status="partial")]))
        self.assertAlmostEqual(result.metrics[0].score, 200 / 3)
        self.assertEqual(result.metrics[2].score, 50)

    def test_empty_actual_is_omission_not_execution_error(self):
        result = self.evaluate(MemoryExtractionGrader, {"memories": ["Alice lives in Beijing"]},
            self.judgment(expected=[self.check(status="omitted", quote="")], actual=[]), [])
        self.assertEqual(result.metrics[0].score, 0)
        self.assertFalse(result.requires_review)

    def test_empty_gold_and_actual_memories_are_a_correct_empty_extraction(self):
        result = self.evaluate(MemoryExtractionGrader, {"memories": []}, self.judgment(expected=[], actual=[]), [])
        self.assertEqual(result.metrics[0].score, 100)

    def test_unchanged_old_memory_is_update_omission(self):
        result = self.evaluate(MemoryUpdateGrader,
            {"updates": [{"before": "Alice lives in Shanghai", "after": "Alice lives in Beijing"}]},
            self.judgment(expected=[self.check(status="omitted", quote="")],
                actual=[self.check(status="unchanged", quote="Alice lives in Shanghai")]), ["Alice lives in Shanghai"])
        self.assertEqual(result.metrics[0].raw_value["classification"], "omission")
        self.assertEqual(result.metrics[0].score, 0)

    def test_old_qa_version_requires_explicit_new_baseline(self):
        self.assertIsNone(EvaluationGraderRegistry.resolve("memory_qa", 1)[0])
        self.assertIs(EvaluationGraderRegistry.resolve("memory_qa", 2)[0], MemoryQAGrader)
        self.assertNotIn("confidence_threshold", EvaluationGraderRegistry.parameter_schema("memory_qa")["properties"])

    def test_update_old_current_fact_conflict_is_hallucination(self):
        result = self.evaluate(MemoryUpdateGrader,
            {"updates": [{"before": "Alice lives in Shanghai", "after": "Alice lives in Beijing"}]},
            self.judgment(actual=[self.check(), self.check(1, "contradicted", "Alice lives in Shanghai")]),
            ["Alice now lives in Beijing", "Alice lives in Shanghai"], threshold=0)
        self.assertEqual(result.metrics[0].raw_value["classification"], "hallucination")
        self.assertFalse(result.metrics[0].passed)

    def test_update_history_can_remain_when_new_fact_is_current(self):
        result = self.evaluate(MemoryUpdateGrader,
            {"updates": [{"before": "Alice lives in Shanghai", "after": "Alice lives in Beijing"}]},
            self.judgment(actual=[self.check(), self.check(1, quote="Alice lived in Shanghai in January")]),
            ["Alice now lives in Beijing", "Alice lived in Shanghai in January"])
        self.assertEqual(result.metrics[0].score, 100)

    def test_hallucination_has_priority_over_missing_necessary_fact(self):
        result = self.evaluate(MemoryQAGrader, {"answer": "Beijing", "facts": ["Beijing", "February"]},
            self.judgment(expected=[self.check(quote="Beijing"), self.check(1, "omitted", "")],
                actual=[self.check(status="partial", quote="Beijing, she is a doctor")]), "Beijing, she is a doctor")
        self.assertEqual(result.metrics[0].raw_value["classification"], "hallucination")
        self.assertEqual(result.metrics[0].score, 0)

    def test_low_self_reported_confidence_alone_does_not_invalidate(self):
        result = self.evaluate(MemoryQAGrader, {"answer": "Beijing"}, self.judgment(confidence=0.1), "Alice now lives in Beijing")
        self.assertEqual(result.metrics[0].score, 100)
        self.assertFalse(result.requires_review)

    def test_unjustified_abstention_is_omission_not_hallucination(self):
        abstained = self.check(status="abstained", quote="不知道")
        abstained["source_quote"] = ""
        result = self.evaluate(MemoryQAGrader, {"answer": "Beijing"},
            self.judgment(expected=[self.check(status="omitted", quote="")], actual=[abstained]), "不知道")
        self.assertEqual(result.metrics[0].raw_value["classification"], "omission")
        self.assertEqual(result.metrics[0].score, 0)

    def test_unsupported_extracted_fact_does_not_require_fabricated_source_quote(self):
        unsupported = self.check(status="unsupported", quote="Alice is a doctor")
        unsupported["source_quote"] = ""
        result = self.evaluate(MemoryExtractionGrader, {"memories": ["Alice lives in Beijing"]},
            self.judgment(expected=[self.check(status="omitted", quote="")], actual=[unsupported]), ["Alice is a doctor"])
        self.assertEqual(result.metrics[0].score, 0)
        self.assertFalse(result.requires_review)

    def test_invalid_fact_coverage_or_fabricated_citations_is_unscored(self):
        base = self.judgment()
        variants = [self.judgment(expected=[]), self.judgment(actual=[]), self.judgment(expected=[self.check(), self.check()]),
                    self.judgment(expected=[self.check(index=10)]), self.judgment(requires_review=True),
                    self.judgment(actual=[self.check(status="unverifiable")])]
        bad_source = deepcopy(base)
        bad_source["actual_checks"][0]["source_quote"] = "Fabricated evidence"
        variants.append(bad_source)
        bad_answer = deepcopy(base)
        bad_answer["actual_checks"][0]["actual_quote"] = "not in actual output"
        variants.append(bad_answer)
        for judgment in variants:
            with self.subTest(judgment=judgment):
                result = self.evaluate(MemoryQAGrader, {"answer": "Beijing"}, judgment, "Alice now lives in Beijing")
                self.assertIsNone(result.metrics[0].score)
                self.assertTrue(result.requires_review)

    def test_missing_source_and_invalid_contract_rejected_before_model_call(self):
        with patch("src.apps.evaluation.services.memory_grading.json_chat") as chat:
            for grader, gold, actual in [(MemoryExtractionGrader, {"memories": "bad"}, []),
                (MemoryUpdateGrader, {"updates": [{"after": "Beijing"}]}, []),
                (MemoryQAGrader, {"answer": "Beijing", "facts": []}, "Beijing")]:
                with self.assertRaises(EvaluationError):
                    grader.evaluate(dataset_item={"expected_output": gold, "context": {"source_evidence": [self.source]}},
                        actual=actual, config={}, metric_key="m", threshold=100)
            chat.assert_not_called()
            with self.assertRaises(EvaluationError):
                MemoryQAGrader.evaluate(dataset_item={"expected_output": {"answer": "Beijing"}},
                    actual="Beijing", config={}, metric_key="m", threshold=100)
            chat.assert_not_called()
