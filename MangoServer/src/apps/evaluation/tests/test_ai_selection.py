from unittest.mock import patch
from types import SimpleNamespace
from django.test import SimpleTestCase
from src.apps.evaluation.exceptions import EvaluationError
from src.apps.evaluation.services.validation import invalid_config
from src.apps.evaluation.services.ai import model_snapshot, json_chat, ai_options
from src.apps.system.services.ai.evaluation_profiles import EvaluationAiProfileService
from src.apps.system.services.ai.client import AiConfig
from src.apps.system.constants import EVALUATION_DEFAULT_AI_PROFILE_ID


class EvaluationAiSelectionTests(SimpleTestCase):
    def test_answer_budget_caps_timeout_without_changing_frozen_configuration(self):
        with patch.object(EvaluationAiProfileService, "resolve", return_value=(self.profile, self.config)), patch("src.apps.evaluation.services.ai.AiService.json_chat") as chat:
            frozen = model_snapshot("judge", "evaluation.memory")
            original_timeout = self.config.timeout
            json_chat(frozen=frozen, prompt_id="evaluation.memory", timeout_seconds=2, messages=[])
            self.assertEqual(chat.call_args.kwargs["config"].timeout, 2)
            self.assertEqual(self.config.timeout, original_timeout)
            self.assertEqual(model_snapshot("judge", "evaluation.memory"), frozen)

    def setUp(self):
        self.profile = SimpleNamespace(id="judge", name="评分 AI")
        self.config = AiConfig("openai_compatible", "test-only-key", "https://example.com/v1", "judge-model", 120)

    def test_no_implicit_default_ai(self):
        with patch("src.apps.evaluation.services.ai.AiService.load_config") as default:
            with self.assertRaises(EvaluationError):
                model_snapshot(None, "evaluation.memory")
            default.assert_not_called()

    @patch.object(EvaluationAiProfileService, "resolve")
    @patch("src.apps.evaluation.services.ai.AiService.json_chat")
    def test_selected_profile_is_used_and_semantic_drift_is_rejected(self, chat, resolve):
        resolve.return_value = self.profile, self.config
        frozen = model_snapshot("judge", "evaluation.judge")
        self.assertNotIn("test-only-key", str(frozen))
        json_chat(frozen=frozen, prompt_id="evaluation.judge", messages=[])
        self.assertIs(chat.call_args.kwargs["config"], self.config)
        self.config.model = "changed"
        with self.assertRaises(EvaluationError):
            json_chat(frozen=frozen, prompt_id="evaluation.judge", messages=[])
        self.assertEqual(chat.call_count, 1)

    @patch("src.apps.evaluation.selectors.case.get_case", side_effect=invalid_config("无权访问测试用例"))
    @patch.object(EvaluationAiProfileService, "options")
    def test_option_lookup_checks_case_scope_first(self, options, case):
        with self.assertRaises(EvaluationError):
            ai_options(100, object())
        options.assert_not_called()

    @patch("src.apps.evaluation.services.ai.AiService.json_chat")
    @patch("src.apps.evaluation.services.ai.AiService.load_config")
    @patch.object(EvaluationAiProfileService, "profiles")
    def test_explicit_default_selection_is_frozen_and_used_without_copying_keys(self, profiles, default, chat):
        profiles.return_value = []
        default.return_value = self.config
        for prompt in ("evaluation.judge", "evaluation.memory", "evaluation.memory_scoring", "evaluation.summary"):
            frozen = model_snapshot(EVALUATION_DEFAULT_AI_PROFILE_ID, prompt)
            self.assertEqual(frozen["name"], "系统默认 AI")
            self.assertNotIn("test-only-key", str(frozen))
            json_chat(frozen=frozen, prompt_id=prompt, messages=[])
            self.assertIs(chat.call_args.kwargs["config"], self.config)
        self.config.api_key = "rotated-test-key"
        json_chat(frozen=frozen, prompt_id="evaluation.summary", messages=[])
        self.config.model = "changed-model"
        with self.assertRaises(EvaluationError):
            json_chat(frozen=frozen, prompt_id="evaluation.summary", messages=[])
        profiles.assert_not_called()
