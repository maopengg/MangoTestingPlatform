import json
from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase
from src.apps.evaluation.schemas.answer import EvaluationAnswering, EvaluationAnswerModelSnapshot
from src.apps.evaluation.services.answer import answer_model_snapshot, generate_answer
from src.apps.evaluation.services.ai import model_snapshot
from src.apps.evaluation.services.execution import EvaluationCaseExecutionService
from src.apps.evaluation.services.graders import MemoryQAGrader
from src.apps.evaluation.services.grading import validate_bindings
from src.apps.evaluation.schemas.case import EvaluationGraderBinding
from src.apps.evaluation.exceptions import EvaluationError
from src.apps.evaluation.services.validation import invalid_config


class MemoryQATests(SimpleTestCase):
    def setUp(self):
        resolver = patch("src.apps.evaluation.services.ai.EvaluationAiProfileService.resolve",
            return_value=(SimpleNamespace(id="test-ai", name="测试 AI"), self.model()))
        resolver.start()
        self.addCleanup(resolver.stop)

    def model(self):
        return SimpleNamespace(provider_type="openai_compatible", model="example-model", base_url="https://example.com/v1", timeout=120)

    def sample(self):
        return {"input_data": {"query": "Where does Alice live now?"},
                "expected_output": {"answer": "Beijing"}, "context": {"source_evidence": [{"excerpt": "Alice moved to Beijing."}]}}

    def judgment(self, category="correct", quote="Beijing", reference="Alice moved to Beijing."):
        return {"confidence": 0.95, "requires_review": False, "reason": "根据原文核对回答",
                "expected_checks": [{"index": 0, "status": {"correct": "supported", "hallucination": "contradicted", "omission": "omitted"}[category],
                                     "actual_quote": quote, "source_quote": reference, "reason": "核对必要事实"}],
                "actual_checks": [{"index": 0, "status": "contradicted" if category == "hallucination" else "supported",
                                   "actual_quote": quote, "source_quote": reference, "reason": "核对回答事实"}]}

    def judge_snapshot(self):
        return model_snapshot("test-ai", "evaluation.memory_scoring")

    def test_answer_generation_never_receives_gold_or_annotation(self):
        sample = self.sample()
        sample["context"]["annotation"] = "GOLD_ONLY_MARKER"
        with patch("src.apps.evaluation.services.ai.AiService.json_chat", return_value={"choices": [{"message": {"content": {"answer": "Beijing"}}}]}) as chat:
            frozen = EvaluationAnswerModelSnapshot.model_validate(answer_model_snapshot("test-ai"))
            result = generate_answer(settings=EvaluationAnswering(), frozen_model=frozen,
                dataset_item=SimpleNamespace(**sample), retrieved=[{"content": "Alice moved to Beijing."}])
        payload = json.loads(chat.call_args.kwargs["messages"][1]["content"])
        self.assertEqual(set(payload), {"question", "memories"})
        self.assertEqual(payload["memories"], [{"content": "Alice moved to Beijing."}])
        self.assertNotIn("GOLD_ONLY_MARKER", json.dumps(payload))
        self.assertEqual(result["answer"], "Beijing")
        self.assertIn("retrieval", result)

    def test_model_change_rejects_before_generation(self):
        with patch("src.apps.evaluation.services.ai.AiService.json_chat") as chat:
            snapshot = {**answer_model_snapshot("test-ai"), "model": "changed-model"}
            with self.assertRaises(EvaluationError):
                generate_answer(settings=EvaluationAnswering(), frozen_model=EvaluationAnswerModelSnapshot(**snapshot), dataset_item=SimpleNamespace(**self.sample()), retrieved={"top_items": []})
            chat.assert_not_called()

    def test_judge_distinguishes_categories_and_checks_quote_grounding(self):
        for category, answer, quote, expected_score, review in [
            ("correct", "Beijing", "Beijing", 100, False),
            ("hallucination", "Shanghai", "Shanghai", 0, False),
            ("omission", "I do not know", "I do not know", 0, False),
            ("correct", "Beijing", "not in answer", None, True),
        ]:
            with self.subTest(category=category, quote=quote), patch("src.apps.evaluation.services.ai.AiService.json_chat", return_value={"choices": [{"message": {"content": self.judgment(category, quote)}}]}):
                result = MemoryQAGrader.evaluate(dataset_item=self.sample(), actual={"answer": answer}, config={"_judge_snapshot": self.judge_snapshot()}, metric_key="qa", threshold=100)
                self.assertEqual(result.metrics[0].score, expected_score)
                self.assertEqual(result.requires_review, review)
                self.assertEqual(result.metrics[0].raw_value["classification"], category)

    def test_retrieval_cannot_be_mistaken_for_final_answer(self):
        with patch("src.apps.evaluation.services.ai.AiService.json_chat") as chat:
            with self.assertRaises(EvaluationError):
                MemoryQAGrader.evaluate(dataset_item=self.sample(), actual={"top_items": []}, config={}, metric_key="qa", threshold=100)
            chat.assert_not_called()

    def test_direct_answer_text_can_be_judged(self):
        with patch("src.apps.evaluation.services.ai.AiService.json_chat", return_value={"choices": [{"message": {"content": self.judgment()}}]}):
            result = MemoryQAGrader.evaluate(dataset_item=self.sample(), actual="Beijing", config={"_judge_snapshot": self.judge_snapshot()}, metric_key="qa", threshold=100)
        self.assertEqual(result.metrics[0].score, 100)

    def test_ai_classification_cannot_be_a_hard_gate(self):
        with self.assertRaises(EvaluationError):
            validate_bindings([EvaluationGraderBinding(grader_key="memory_qa", grader_version=2, metric_key="qa", hard_gate=True)])

    def test_zero_threshold_does_not_make_hallucination_pass(self):
        with patch("src.apps.evaluation.services.ai.AiService.json_chat", return_value={"choices": [{"message": {"content": self.judgment("hallucination", "Shanghai")}}]}):
            result = MemoryQAGrader.evaluate(dataset_item=self.sample(), actual={"answer": "Shanghai"}, config={"_judge_snapshot": self.judge_snapshot()}, metric_key="qa", threshold=0)
        self.assertFalse(result.metrics[0].passed)

    def test_generation_failure_is_invalid_even_if_retrieval_succeeded(self):
        from unittest.mock import MagicMock
        from src.apps.evaluation.models import EvaluationItemResult
        from src.apps.evaluation.schemas.case import EvaluationGradingConfig
        row = EvaluationItemResult(pk=1, item_snapshot={"effective_graders": []})
        adapter = MagicMock()
        adapter.execute.return_value = {"output": {"top_items": []}}
        config = SimpleNamespace(answering=EvaluationAnswering(), answer_model=None,
            execution=SimpleNamespace(retry_count=0, item_timeout_seconds=600), grading=EvaluationGradingConfig())
        with patch.object(EvaluationCaseExecutionService, "_save_grade_results"), patch.object(EvaluationItemResult, "save"), patch.object(EvaluationItemResult, "grade_results", MagicMock()), patch("src.apps.evaluation.services.execution.EvaluationAttemptService.start", return_value=1), patch("src.apps.evaluation.services.execution.EvaluationAttemptService.finish"), patch("src.apps.evaluation.services.execution.generate_answer", side_effect=invalid_config("模拟回答生成失败")):
            EvaluationCaseExecutionService._execute_item_core(SimpleNamespace(created_by_id=1), row, config, adapter, SimpleNamespace(executor_config={}), SimpleNamespace(), SimpleNamespace())
        self.assertEqual(row.execution_status, "failed")
        self.assertEqual(row.verdict, "invalid")

    def test_invalid_judgments_are_excluded_and_repeated_valid_judgments_are_observations(self):
        rows = [SimpleNamespace(id=1, dataset_item_id="A", grade_status="graded"),
                SimpleNamespace(id=2, dataset_item_id="B", grade_status="invalid"),
                SimpleNamespace(id=3, dataset_item_id="C", grade_status="graded"),
                SimpleNamespace(id=4, dataset_item_id="C", grade_status="graded")]
        grades = [{"item_result_id": key, "raw_value": {"classification": category}} for key, category in [(1, "correct"), (2, "hallucination"), (3, "correct"), (4, "omission")]]
        summary = EvaluationCaseExecutionService._memory_qa_summary(rows, grades)
        self.assertEqual(summary["valid"], 3)
        self.assertEqual(summary["invalid"], 1)
        self.assertEqual(summary["rates"]["correct"], 0.6667)
