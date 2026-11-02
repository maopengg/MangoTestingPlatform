from src.apps.user.services.http_permission_registry import permission_for_view
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from src.apps.auto_api.api.serializers.api_auth_config_mutation import ApiAuthConfigSerializers
from src.apps.auto_api.api.views.api_auth_config import ApiAuthConfigViews, ApiAuthConfigCRUD
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.models import ApiAuthConfig
from src.apps.auto_api.services.api_auth_config import ApiAuthConfigService
from src.apps.auto_api.services.api_case.global_variable import ApiCaseGlobalVariableService
from src.apps.auto_api.services.base.api_base_test_setup.auth_manager import ApiAuthManager
from src.common.testing import ObtainTestData
from src.interfaces.mcp.tools.api.auth_config import _write_payload, register_api_auth_config_tools


class AuthTargetTests(SimpleTestCase):
    def test_rest_normalizes_null_optional_values_before_field_validation(self):
        payload = {'target_address': None, 'public_variable_ids': None}
        serializer = ApiAuthConfigSerializers(data=payload, partial=True)
        serializer.validators = []
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['target_address'], '')
        self.assertEqual(serializer.validated_data['public_variable_ids'], [])
        self.assertIsNone(payload['target_address'])
        self.assertIsNone(payload['public_variable_ids'])

    def test_service_normalizes_explicit_null_without_clearing_omitted_fields(self):
        instance = SimpleNamespace(target_address='', public_variable_ids=[])
        data = {'target_address': None, 'public_variable_ids': None}
        self.assertEqual(ApiAuthConfigService.validate_payload(instance, data), {})
        self.assertEqual(data['target_address'], '')
        self.assertEqual(data['public_variable_ids'], [])
        serializer = ApiAuthConfigSerializers(
            instance=ApiAuthConfig(auth_type=1, custom_code='def auth(context): return {}'), data={}, partial=True)
        serializer.validators = []
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('target_address', serializer.validated_data)
        self.assertNotIn('public_variable_ids', serializer.validated_data)
        self.assertEqual(ApiAuthConfigService.normalize_optional_values({}), {})

    def test_invalid_optional_values_are_still_rejected(self):
        for payload in ({'public_variable_ids': 'bad'}, {'public_variable_ids': [0]},
                        {'target_address': ['bad']}):
            with self.subTest(payload=payload):
                serializer = ApiAuthConfigSerializers(data=payload, partial=True)
                self.assertFalse(serializer.is_valid())
                self.assertIn(next(iter(payload)), serializer.errors)

    def target(self):
        return SimpleNamespace(project_product_id=1, environment=0, value='', target_config={
            'default': 'https://example.com', 'selector': 'tenant_id',
            'mapping': {'other': 'https://example.org', 'same-host': 'https://example.org'},
        })

    def test_optional_model_and_payload_preserve_default_and_explicit_clear(self):
        field = ApiAuthConfig._meta.get_field('target_address')
        self.assertTrue(field.blank)
        self.assertEqual(field.default, '')
        self.assertNotIn('target_address', _write_payload())
        self.assertEqual(_write_payload(target_address='')['target_address'], '')
        self.assertEqual(_write_payload(include_none=True)['target_address'], '')

    def test_options_default_mapping_deduplication_and_fixed_address(self):
        options = ApiAuthConfigService.options_for_target(self.target())
        self.assertEqual([item['value'] for item in options], ['https://example.com', 'https://example.org'])
        target = self.target()
        target.value = 'https://example.net'
        self.assertEqual(ApiAuthConfigService.options_for_target(target), [
            {'value': 'https://example.net', 'label': '默认地址 / https://example.net'}])

    def test_foreign_address_is_rejected_and_empty_needs_no_lookup(self):
        with patch.object(ApiAuthConfigService, 'target_options', return_value=[{'value': 'https://example.com'}]) as options:
            ApiAuthConfigService.validate_target_address('', 1, 0)
            options.assert_not_called()
            ApiAuthConfigService.validate_target_address('https://example.com', 1, 0)
            with self.assertRaises(AutoApiError):
                ApiAuthConfigService.validate_target_address('https://example.org', 1, 0)
            options.assert_called_with(1, 0)

    def test_rest_and_service_share_validation(self):
        with patch.object(ApiAuthConfigService, 'validate_target_address') as validate:
            ApiAuthConfigSerializers().validate({'auth_type': 1, 'custom_code': 'example',
                'target_address': 'https://example.org', 'project_product': SimpleNamespace(id=1), 'test_env': 0})
            validate.assert_called_once_with('https://example.org', 1, 0)

    def test_only_current_address_authorizations_are_loaded(self):
        data = ObtainTestData()
        data.set_cache('tenant_id', 'other')
        setup = SimpleNamespace(test_object=self.target(), test_data=data, current_api_info_id=None)
        default = SimpleNamespace(id=18, target_address='')
        chosen = SimpleNamespace(id=52, target_address='https://example.org')
        with patch.object(ApiCaseGlobalVariableService, 'list_auth_configs', return_value=[default, chosen]), \
                patch.object(ApiAuthManager, 'load_config') as load:
            ApiAuthManager.load(1, 0, setup, [52])
            load.assert_called_once_with(chosen)

    def test_explicit_nonmatching_authorization_fails_before_refresh(self):
        setup = SimpleNamespace(test_object=self.target(), test_data=ObtainTestData(), current_api_info_id=None)
        with patch.object(ApiCaseGlobalVariableService, 'list_auth_configs', return_value=[
                SimpleNamespace(id=52, target_address='https://example.org')]), \
                patch.object(ApiAuthManager, 'load_config') as load:
            with self.assertRaises(AutoApiError):
                ApiAuthManager.load(1, 0, setup, [52])
            load.assert_not_called()

    def test_multiple_selected_domains_only_load_matching_one(self):
        setup = SimpleNamespace(test_object=self.target(), test_data=ObtainTestData(), current_api_info_id=None)
        first = SimpleNamespace(id=18, target_address='')
        second = SimpleNamespace(id=52, target_address='https://example.org')
        with patch.object(ApiCaseGlobalVariableService, 'list_auth_configs', return_value=[first, second]), \
                patch.object(ApiAuthManager, 'load_config') as load:
            ApiAuthManager.load(1, 0, setup, [18, 52])
            load.assert_called_once_with(first)

    def test_scope_changes_with_address_but_not_case_variables(self):
        setup = SimpleNamespace(test_object=self.target(), test_data=ObtainTestData())
        config = SimpleNamespace(project_product_id=1, test_env=0, target_address='https://example.org')
        manager = ApiAuthManager(setup)
        scope = manager._target_scope(config)
        setup.test_data.set_cache('tenant_id', 'other')
        self.assertEqual(manager._target_scope(config), scope)
        config.target_address = ''
        self.assertNotEqual(manager._target_scope(config), scope)

    def test_refresh_pins_address_without_inheriting_case_tenant(self):
        child = MagicMock()
        child.test_object = self.target()
        child.test_data = ObtainTestData()
        child.init_public.side_effect = lambda *args: child.test_data.set_cache('tenant_id', 'default')
        caller_data = ObtainTestData()
        caller_data.set_cache('tenant_id', 'other')
        manager = ApiAuthManager(SimpleNamespace(test_data=caller_data))
        config = SimpleNamespace(project_product_id=1, test_env=0, public_variable_ids=[], target_address='https://example.org')
        def authenticate(config):
            self.assertEqual(child.test_object.value, 'https://example.org')
            self.assertEqual(child.test_data.get_cache('url'), 'https://example.org')
            self.assertEqual(child.test_data.get_cache('tenant_id'), 'default')
            return {'token': 'example'}
        with patch('src.apps.auto_api.services.base.api_base_test_setup.APIBaseTestSetup', return_value=child), \
                patch.object(manager, '_refresh_cache_data', side_effect=authenticate):
            manager._refresh_in_isolated_context(config)
        self.assertEqual(caller_data.get_cache('tenant_id'), 'other')

    def test_target_options_enforce_product_scope_before_read(self):
        request = APIRequestFactory().get('/api/api/auth/config/targets', {'project_product': 1, 'test_env': 0})
        with patch.object(ApiAuthConfigCRUD, 'has_data_scope_permission', return_value=False), \
                patch.object(ApiAuthConfigService, 'target_options') as options:
            ApiAuthConfigViews.as_view({'get': 'targets'})(request)
            options.assert_not_called()
        self.assertEqual(permission_for_view(ApiAuthConfigViews, 'targets'),
                         ('api.auth_config:add', 'api.auth_config:change'))

    def test_mcp_tools_forward_optional_address_and_describe_default(self):
        registry = SimpleNamespace(tools={})
        def register():
            def decorator(function):
                registry.tools[function.__name__] = function
                return function
            return decorator
        registry.tool = register
        register_api_auth_config_tools(registry)
        with patch.object(ApiAuthConfigService, 'create', return_value={'id': 1}) as create, \
                patch.object(ApiAuthConfigService, 'update', return_value={'id': 1}) as update, \
                patch('src.interfaces.mcp.tools.api.auth_config.mcp_current_user_id', return_value=9):
            registry.tools['create_api_auth_config'](1, 0, 'Example', target_address='https://example.org')
            self.assertEqual(create.call_args.args[0]['target_address'], 'https://example.org')
            registry.tools['update_api_auth_config'](1, target_address='')
            self.assertEqual(update.call_args.args[1]['target_address'], '')
            registry.tools['update_api_auth_config'](1)
            self.assertNotIn('target_address', update.call_args.args[1])
