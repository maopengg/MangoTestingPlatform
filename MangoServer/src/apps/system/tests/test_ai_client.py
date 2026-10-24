from copy import deepcopy
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.ai.exceptions import AiError
from src.apps.system.services.ai.client import AiConfig, AiService, OpenAiCompatibleClient


class AiClientTest(SimpleTestCase):
    @patch("src.apps.system.services.ai.client.SystemConfigService.get")
    def test_load_config_cleans_invisible_model_name_characters(self, get_config):
        values = {
            "AI_PROVIDER_TYPE": "openai_compatible",
            "AI_API_KEY": "key",
            "AI_BASE_URL": "https://example.com/v1",
            "AI_MODEL": "deepseek-v4-flash\u200b",
            "AI_TIMEOUT": 600,
        }
        get_config.side_effect = lambda key, default=None: values.get(key, default)

        config = AiService.load_config()

        self.assertEqual(config.model, "deepseek-v4-flash")

    @patch("src.apps.system.services.ai.client.SystemConfigService.get")
    def test_vision_config_inherits_main_model_by_default(self, get_config):
        values = {
            "AI_VISION_USE_SEPARATE_CONFIG": False,
            "AI_PROVIDER_TYPE": "openai_compatible",
            "AI_API_KEY": "main-key",
            "AI_BASE_URL": "https://example.com/v1",
            "AI_MODEL": "multimodal-model",
            "AI_TIMEOUT": 600,
            "AI_VISION_TIMEOUT": 30,
        }
        get_config.side_effect = lambda key, default=None: values.get(key, default)

        config = AiService.load_vision_config()

        self.assertEqual(config.api_key, "main-key")
        self.assertEqual(config.model, "multimodal-model")
        self.assertEqual(config.timeout, 30)
        self.assertIsNone(config.proxy_url)

    @patch("src.apps.system.services.ai.client.SystemConfigService.get")
    def test_separate_vision_config_overrides_main_model(self, get_config):
        values = {
            "AI_VISION_USE_SEPARATE_CONFIG": True,
            "AI_VISION_PROVIDER_TYPE": "openai_compatible",
            "AI_VISION_API_KEY": "vision-key",
            "AI_VISION_BASE_URL": "https://vision.example.com/v1",
            "AI_VISION_MODEL": "vision-model",
            "AI_VISION_TIMEOUT": 45,
            "AI_VISION_PROXY_URL": "https://proxy.example.com",
        }
        get_config.side_effect = lambda key, default=None: values.get(key, default)

        config = AiService.load_vision_config()

        self.assertEqual(config.api_key, "vision-key")
        self.assertEqual(config.model, "vision-model")
        self.assertEqual(config.timeout, 45)
        self.assertEqual(config.proxy_url, "https://proxy.example.com")

    @patch("src.apps.system.services.ai.client.requests.post")
    def test_chat_sends_disabled_thinking_for_short_json_task(self, request_post):
        response = Mock(status_code=200)
        response.json.return_value = {"choices": [{"message": {"content": "{}"}}]}
        request_post.return_value = response
        client = OpenAiCompatibleClient(self._config())

        client.chat(
            messages=[{"role": "user", "content": "return json"}],
            response_format={"type": "json_object"},
            max_tokens=5000,
            thinking={"type": "disabled"},
        )

        payload = request_post.call_args.kwargs["json"]
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertEqual(payload["max_tokens"], 5000)

    @patch("src.apps.system.services.ai.client.requests.post")
    def test_chat_retries_without_thinking_when_model_rejects_parameter(self, request_post):
        unsupported_response = Mock(status_code=400)
        unsupported_response.json.return_value = {
            "error": {
                "code": "1210",
                "message": "该模型始终思考，不支持关闭思考；请使用 low、high 或 max。",
            }
        }
        success_response = Mock(status_code=200)
        success_response.json.return_value = {
            "choices": [{"message": {"content": "{}"}}]
        }
        responses = iter([unsupported_response, success_response])
        sent_payloads = []

        def post_side_effect(*_args, **kwargs):
            sent_payloads.append(deepcopy(kwargs["json"]))
            return next(responses)

        request_post.side_effect = post_side_effect
        client = OpenAiCompatibleClient(self._config())

        result = client.chat(
            messages=[{"role": "user", "content": "return json"}],
            thinking={"type": "disabled"},
        )

        self.assertEqual(result, success_response.json.return_value)
        self.assertEqual(request_post.call_count, 2)
        first_payload, second_payload = sent_payloads
        self.assertEqual(first_payload["thinking"], {"type": "disabled"})
        self.assertNotIn("thinking", second_payload)

    @patch("src.apps.system.services.ai.client.requests.post")
    def test_chat_retries_without_thinking_only_once(self, request_post):
        response = Mock(status_code=400)
        response.json.return_value = {
            "error": {"message": "thinking is not supported by this model"}
        }
        request_post.return_value = response
        client = OpenAiCompatibleClient(self._config())

        with self.assertRaisesMessage(AiError, "thinking is not supported"):
            client.chat(
                messages=[{"role": "user", "content": "return json"}],
                thinking={"type": "disabled"},
            )

        self.assertEqual(request_post.call_count, 2)

    @staticmethod
    def _config() -> AiConfig:
        return AiConfig(
            provider_type="openai_compatible",
            api_key="key",
            base_url="https://example.com/v1",
            model="model",
            timeout=600,
        )
