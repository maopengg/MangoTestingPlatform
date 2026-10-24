from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch

from src.network.http.apis.system import SystemApi
from src.services.runtime_config import get_ai_config, set_ai_config
from src.services.ui.element_locator_engine import UiElementLocatorEngine
from src.services.ui.element_healing.harness_factory import create_ui_element_healing_harness
from src.services.ui.element_healing.platform_model_client import PlatformModelClient
from src.services.ui.element_healing.platform_vision_model_client import PlatformVisionModelClient
from src.services.ui.element_healing.runtime_config import PlatformRuntimeConfig
from src.settings import settings


class PlatformRuntimeConfigTest(TestCase):
    @patch(
        'src.services.ui.element_healing.runtime_config.get_task_ui_runtime_config',
        return_value={'visual_locator_enabled': True},
    )
    def test_visual_locator_uses_task_snapshot(self, _runtime_config):
        self.assertTrue(PlatformRuntimeConfig().visual_locator_enabled())

    def test_platform_harnesses_create_visual_agent(self):
        self.assertIsNotNone(UiElementLocatorEngine().visual_agent)
        self.assertIsNotNone(create_ui_element_healing_harness().visual_agent)

    @patch('src.services.ui.element_healing.runtime_config.get_ai_config')
    def test_visual_timeout_is_exposed_to_healing_budget(self, get_config):
        get_config.return_value = SimpleNamespace(vision_timeout=54)

        self.assertEqual(PlatformRuntimeConfig().visual_locator_timeout_seconds(), 54)


class VisionRuntimeConfigRefreshTest(IsolatedAsyncioTestCase):
    async def test_default_vision_config_inherits_main_model(self):
        previous_config = get_ai_config()
        api = SystemApi(
            SimpleNamespace(),
            SimpleNamespace(get_headers=lambda: {}),
        )
        api.get_config_values = AsyncMock(return_value={
            'AI_PROVIDER_TYPE': 'openai_compatible',
            'AI_API_KEY': 'main-key',
            'AI_BASE_URL': 'https://example.com/v1',
            'AI_MODEL': 'multimodal-model',
            'AI_TIMEOUT': 600,
            'AI_VISION_USE_SEPARATE_CONFIG': False,
            'AI_VISION_TIMEOUT': 30,
            'UI_VISUAL_LOCATOR_ENABLED': True,
            'UI_FIXED_LOCATOR_RETRY_SECONDS': 10,
            'UI_SMART_LOCATOR_TIMEOUT_SECONDS': 30,
            'EXECUTOR_MAX_CONCURRENT_TASKS': 5,
            'EXECUTOR_MEMORY_THRESHOLD_PERCENT': 100,
            'UI_LIVE_WORKSPACE_MAX_USERS': 5,
            'PERF_EXECUTOR_MAX_CONCURRENT_RUNS': 5,
        })
        try:
            await api.refresh_runtime_config()
            config = get_ai_config()
            self.assertTrue(config.visual_locator_enabled)
            self.assertEqual(config.vision_api_key, 'main-key')
            self.assertEqual(config.vision_model, 'multimodal-model')
            self.assertEqual(config.vision_timeout, 30)
        finally:
            set_ai_config(previous_config)


class PlatformModelClientDebugLogTest(TestCase):
    @patch('src.services.ui.element_healing.platform_model_client.log')
    @patch('src.services.ui.element_healing.platform_model_client.get_ai_config')
    def test_debug_logs_sanitized_ai_request_and_response(self, get_config, logger):
        get_config.return_value = SimpleNamespace(
            locator_enabled=True,
            api_key='must-not-appear',
            provider_type='openai_compatible',
            base_url='https://example.com/v1',
            model='test-model',
            timeout=30,
        )
        inner_client = MagicMock()
        inner_client.complete_sync.return_value = (
            '{"status":"matched","reason":"authorization=private-value"}'
        )
        model_client = PlatformModelClient()
        model_client._get_client = MagicMock(return_value=inner_client)
        long_debug_marker = 'x' * 2500 + 'END_OF_AI_REQUEST'

        with patch.object(settings, 'IS_DEBUG', True):
            result = model_client.complete_sync(
                [{'role': 'user', 'content': f'token=private-value {long_debug_marker}'}],
                max_tokens=100,
                temperature=0,
                response_format={'type': 'json_object'},
            )

        self.assertIn('matched', result)
        self.assertEqual(logger.debug.call_count, 2)
        request_log = logger.debug.call_args_list[0].args[0]
        response_log = logger.debug.call_args_list[1].args[0]
        self.assertIn('[元素智能定位AI请求]', request_log)
        self.assertIn('[元素智能定位AI响应]', response_log)
        self.assertIn('[REDACTED]', request_log)
        self.assertIn('[REDACTED]', response_log)
        self.assertIn('END_OF_AI_REQUEST', request_log)
        self.assertNotIn('private-value', request_log + response_log)
        self.assertNotIn('must-not-appear', request_log + response_log)

    @patch('src.services.ui.element_healing.platform_model_client.log')
    def test_ai_payload_is_not_logged_when_debug_is_disabled(self, logger):
        inner_client = MagicMock()
        inner_client.complete_sync.return_value = '{}'
        model_client = PlatformModelClient()
        model_client._get_client = MagicMock(return_value=inner_client)

        with patch.object(settings, 'IS_DEBUG', False):
            model_client.complete_sync(
                [{'role': 'user', 'content': 'locate e1'}],
                max_tokens=100,
                temperature=0,
            )

        logger.debug.assert_not_called()


class PlatformVisionModelClientTest(TestCase):
    @patch('src.services.ui.element_healing.platform_vision_model_client.OpenAICompatibleModelClient')
    @patch('src.services.ui.element_healing.platform_vision_model_client.get_ai_config')
    def test_visual_timeout_and_provider_are_applied_to_client(self, get_config, client_class):
        get_config.return_value = SimpleNamespace(
            visual_locator_enabled=True,
            vision_provider_type='openai_compatible',
            vision_api_key='vision-key',
            vision_base_url='https://example.com/v1',
            vision_model='vision-model',
            vision_timeout=54,
            vision_proxy_url=None,
        )

        PlatformVisionModelClient()._get_client()

        client_class.assert_called_once_with(
            'vision-key',
            'https://example.com/v1',
            'vision-model',
            54,
            proxy_url=None,
            max_timeout_seconds=54,
        )

    @patch('src.services.ui.element_healing.platform_vision_model_client.get_ai_config')
    def test_unsupported_visual_provider_is_unavailable(self, get_config):
        get_config.return_value = SimpleNamespace(
            visual_locator_enabled=True,
            vision_provider_type='unsupported-provider',
            vision_api_key='vision-key',
            vision_base_url='https://example.com/v1',
            vision_model='vision-model',
        )

        self.assertFalse(PlatformVisionModelClient().available)

    @patch('src.services.ui.element_healing.platform_vision_model_client.log')
    @patch('src.services.ui.element_healing.platform_vision_model_client.get_ai_config')
    def test_visual_debug_log_omits_image_data_and_sensitive_values(self, get_config, logger):
        get_config.return_value = SimpleNamespace(
            visual_locator_enabled=True,
            vision_provider_type='openai_compatible',
            vision_api_key='must-not-appear',
            vision_base_url='https://example.com/v1',
            vision_model='vision-model',
            vision_timeout=30,
            vision_proxy_url=None,
        )
        inner_client = MagicMock()
        inner_client.complete_sync.return_value = '{"status":"not_found"}'
        model_client = PlatformVisionModelClient()
        model_client._get_client = MagicMock(return_value=inner_client)
        messages = [{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': 'token=private-value'},
                {
                    'type': 'image_url',
                    'image_url': {'url': 'data:image/jpeg;base64,SECRET_IMAGE_BYTES'},
                },
            ],
        }]

        with patch.object(settings, 'IS_DEBUG', True):
            model_client.complete_sync(messages, max_tokens=100, temperature=0)

        logs = '\n'.join(call.args[0] for call in logger.debug.call_args_list)
        self.assertIn('[元素视觉定位AI请求]', logs)
        self.assertIn('[IMAGE_DATA_REDACTED]', logs)
        self.assertIn('[REDACTED]', logs)
        self.assertNotIn('SECRET_IMAGE_BYTES', logs)
        self.assertNotIn('private-value', logs)
        self.assertNotIn('must-not-appear', logs)
