from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from mangotools.contracts.test_target import TestTargetConfig
from mangotools.contracts.ui.execution import UiEnvironmentContract
from mangotools.test_target import resolve_test_target
from pydantic import ValidationError

from src.apps.test_center.api.serializers.test_object import TestObjectSerializers
from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.services.environment.test_target import TestTargetService


class TestTargetConfigTests(SimpleTestCase):
    def setUp(self):
        self.config = {'default': 'https://common.example.com', 'selector': '租户id',
                       'mapping': {'1002': 'https://tenant-b.example.com', '1001': 'https://tenant.example.com'},
                       }

    def test_legacy_value_always_wins_even_with_invalid_new_config(self):
        self.assertEqual(resolve_test_target('https://legacy.example.com', {}), 'https://legacy.example.com')

    def test_fixed_target_and_numeric_or_unicode_selector(self):
        self.assertEqual(resolve_test_target('', {'default': 'com.example.demo'}), 'com.example.demo')
        self.assertEqual(resolve_test_target('', self.config, lambda key: '1002'), 'https://tenant-b.example.com')
        self.assertEqual(resolve_test_target('', self.config, lambda key: 1001), 'https://tenant.example.com')

    def test_missing_unknown_complex_values_use_default(self):
        target = SimpleNamespace(value='', target_config=self.config)
        for selected in [None, '9999', [], {}, True]:
            with self.subTest(selected=selected):
                self.assertEqual(TestTargetService.resolve(target, SimpleNamespace(get_cache=lambda key: selected)),
                                 'https://common.example.com')

    def test_old_fallback_flag_no_longer_disables_default(self):
        self.config['fallback_to_default'] = False
        self.assertEqual(resolve_test_target('', self.config), 'https://common.example.com')
        self.assertNotIn('fallback_to_default', TestTargetService.validate(self.config))

    def test_mapping_without_default_is_allowed_but_unmatched_target_fails(self):
        self.config['default'] = ''
        self.assertEqual(TestTargetService.validate(self.config)['default'], '')
        self.assertEqual(resolve_test_target('', self.config, lambda key: '1002'), 'https://tenant-b.example.com')
        with self.assertRaises(TestCenterError):
            TestTargetService.resolve(SimpleNamespace(value='', target_config=self.config))

    def test_invalid_rules(self):
        for config in [{}, {'default': 'x', 'selector': '租户id'},
                       {'selector': '租户id', 'mapping': {}},
                       {'selector': '租户id', 'mapping': {'x': ''}},
                       {'default': 'url', 'extra': True}]:
            with self.subTest(config=config), self.assertRaises(ValidationError):
                TestTargetConfig.model_validate(config)

    def test_selector_is_a_literal_cache_key_not_a_template(self):
        data = {'租户id': '1002'}
        self.assertEqual(resolve_test_target('', self.config, data.get), 'https://tenant-b.example.com')
        config = {**self.config, 'selector': '${{租户id}}'}
        with self.assertRaises(ValidationError):
            TestTargetConfig.model_validate(config)

    def test_serializer_validates_new_without_overwriting_old_value(self):
        serializer = TestObjectSerializers()
        attrs = serializer.validate({'value': '', 'target_config': self.config})
        self.assertEqual(attrs['value'], '')
        self.assertEqual(attrs['target_config'], self.config)
        self.assertEqual(serializer.validate({'value': 'legacy'})['value'], 'legacy')

    def test_shared_ui_contract_round_trip_and_legacy_payload(self):
        packet = UiEnvironmentContract(id=1, test_object_value='', target_config=self.config)
        restored = UiEnvironmentContract.model_validate_json(packet.model_dump_json())
        self.assertEqual(resolve_test_target(restored.test_object_value, restored.target_config, lambda key: '1002'),
                         'https://tenant-b.example.com')
        self.assertIsNone(UiEnvironmentContract(id=1, test_object_value='legacy').target_config)

    def test_resolves_again_after_case_cache_changes(self):
        cache = {'租户id': '1002'}
        first = resolve_test_target('', self.config, cache.get)
        cache['租户id'] = 1001
        self.assertNotEqual(first, resolve_test_target('', self.config, cache.get))

    def test_api_request_uses_current_cache(self):
        from src.apps.auto_api.services.execution.base.api_base_test_setup import APIBaseTestSetup
        from src.common.testing import ObtainTestData
        setup = APIBaseTestSetup.__new__(APIBaseTestSetup)
        setup.test_data = ObtainTestData()
        setup.test_object = SimpleNamespace(value='', target_config=self.config)
        setup.test_data.set_cache('租户id', '1002')
        # 使用已有请求契约构造方式，验证路径拼接发生在变量读取之后。
        request = MagicMock()
        request.__iter__.return_value = []
        request.url = '/api/contracts'
        cleaned = setup.request_data_clean(request)
        self.assertEqual(cleaned.url, 'https://tenant-b.example.com/api/contracts')

    def test_api_auth_fingerprint_isolates_selector_values(self):
        from src.apps.auto_api.services.execution.base.api_base_test_setup.auth_manager import ApiAuthManager
        from src.common.testing import ObtainTestData
        target = SimpleNamespace(value='', target_config=self.config, project_product_id=1, environment=0)
        data = ObtainTestData()
        setup = SimpleNamespace(test_object=target, test_data=data)
        manager = ApiAuthManager(setup)
        config = SimpleNamespace(project_product_id=1, test_env=0)
        data.set_cache('租户id', '1002')
        south = manager._target_scope(config)
        data.set_cache('租户id', 1001)
        self.assertNotEqual(south, manager._target_scope(config))

    def test_dynamic_auth_is_loaded_after_case_variable_is_available(self):
        from src.apps.auto_api.services.execution.base.api_base_test_setup import APIBaseTestSetup
        from src.common.testing import ObtainTestData
        setup = APIBaseTestSetup.__new__(APIBaseTestSetup)
        setup.test_object = SimpleNamespace(value='', target_config=self.config)
        setup.test_data = ObtainTestData()
        setup.test_data.set_cache('租户id', '1002')
        setup.target_auth_scope = (1, 0, [5], 3)
        setup.current_api_info_id = None
        setup.skip_auth_load = False
        request = MagicMock()
        request.__iter__.return_value = []
        request.url = '/api/contracts'
        with patch('src.apps.auto_api.services.execution.base.api_base_test_setup.auth_manager.ApiAuthManager.load') as load:
            setup.request_data_clean(request)
            load.assert_called_once_with(1, 0, setup, [5])
        self.assertIsNone(setup.current_api_info_id)
