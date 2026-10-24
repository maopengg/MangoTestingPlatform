from unittest.mock import patch
from django.test import SimpleTestCase
from src.apps.system.exceptions import SystemError
from src.apps.system.models import CacheData
from src.apps.system.api.serializers.cache_data import CacheDataSerializersC
from src.apps.system.api.views.cache_data import CacheDataViews
from src.apps.system.services.ai.evaluation_profiles import EvaluationAiProfileService, SECRET_MASK
from src.apps.system.services.ai.client import AiConfig
from src.apps.system.constants import EVALUATION_DEFAULT_AI_PROFILE_ID


class EvaluationAiProfilesTests(SimpleTestCase):
    def profile(self, **changes):
        return {"id": "judge-1", "name": "评分模型", "provider_type": "openai_compatible",
                "base_url": "https://example.com/v1", "model": "judge-model", "api_key": "test-only-key",
                "timeout": 120, "enabled": True, **changes}

    def test_duplicate_ids_and_invalid_rows_are_rejected_without_secrets_in_errors(self):
        for value in ({}, [self.profile(), self.profile()], [self.profile(base_url="file:///tmp/model")],
                      [self.profile(api_key="")], [self.profile(timeout=0)], [self.profile(extra="unsupported")],
                      [self.profile(id=EVALUATION_DEFAULT_AI_PROFILE_ID)]):
            with self.subTest(value_type=type(value).__name__), self.assertRaises(SystemError) as error:
                EvaluationAiProfileService.parse(value)
            self.assertNotIn("test-only-key", str(error.exception))

    def test_masked_edit_preserves_only_matching_profile_secret(self):
        rows = EvaluationAiProfileService.masked([self.profile()])
        self.assertEqual(rows[0]["api_key"], SECRET_MASK)
        rows[0]["name"] = "新名称"
        saved = EvaluationAiProfileService.prepare_save(rows, [self.profile()])
        self.assertEqual(saved[0]["api_key"], "test-only-key")
        rows[0]["id"] = "new-id"
        with self.assertRaises(SystemError):
            EvaluationAiProfileService.prepare_save(rows, [self.profile()])

    def test_both_config_read_formats_mask_nested_keys(self):
        import json
        record = CacheData(key="EVALUATION_AI_PROFILES", value=json.dumps([self.profile()]), is_secret=True)
        for output in (CacheDataSerializersC(record).data, CacheDataViews._CacheDataViews__serialize_item(record)):
            self.assertNotIn("test-only-key", json.dumps(output, default=str))
            self.assertEqual(output["value"][0]["api_key"], SECRET_MASK)

    @patch.object(EvaluationAiProfileService, "profiles")
    @patch("src.apps.system.services.ai.client.AiService.load_config")
    def test_case_options_do_not_expose_credentials_or_endpoint(self, default, profiles):
        default.return_value = AiConfig("openai_compatible", "default-test-key", "https://example.org/v1", "default-model", 600)
        profiles.return_value = EvaluationAiProfileService.parse([self.profile()])
        options = EvaluationAiProfileService.options()
        self.assertEqual([row["id"] for row in options], [EVALUATION_DEFAULT_AI_PROFILE_ID, "judge-1"])
        for option in options:
            self.assertEqual(set(option), {"id", "name", "model", "enabled"})
        self.assertNotIn("default-test-key", str(options))
        self.assertNotIn("https://", str(options))

    @patch("src.apps.system.services.ai.client.AiService.load_config")
    @patch.object(EvaluationAiProfileService, "profiles", return_value=[])
    def test_unconfigured_default_is_visible_but_cannot_execute(self, profiles, default):
        default.return_value = AiConfig("openai_compatible", "", "", "", 600)
        option = EvaluationAiProfileService.options()[0]
        self.assertFalse(option["enabled"])
        self.assertEqual(option["disabled_reason"], "未配置完整")
        with self.assertRaises(SystemError):
            EvaluationAiProfileService.resolve(EVALUATION_DEFAULT_AI_PROFILE_ID)
