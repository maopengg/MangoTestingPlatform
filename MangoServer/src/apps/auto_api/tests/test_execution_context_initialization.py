from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.auto_api.enums import ApiPublicTypeEnum
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.schemas.execution import ApiExecutionRequest
from src.apps.auto_api.services.base.api_base_test_setup import APIBaseTestSetup
from src.apps.auto_api.services.base.api_base_test_setup.public_base import PublicBase
from src.apps.auto_api.services.base.api_base_test_setup.auth_manager import ApiAuthManager
from src.apps.auto_api.services.base.case_base import CaseBase
from src.apps.auto_api.services.base.case_data_factory import CaseDataFactory, ParameterDataFactory
from src.apps.auto_api.services.base.case_parameter import CaseParameter
from src.apps.data_factory.models import DataFactoryField
from src.apps.data_factory.services.generator import DataFactoryValueGenerator
from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.exceptions import TEST_TARGET_UNRESOLVED


class ExecutionContextInitializationTests(SimpleTestCase):
    def setup_context(self):
        with patch('src.apps.auto_api.services.base.api_base_test_setup.base_request.CacheDataValue.get_cache_value',
                   return_value=30):
            setup = PublicBase()
        setup.test_object = SimpleNamespace(id=1, project_product_id=1, environment=0, value='', target_config={
            'default': 'https://example.com', 'selector': 'tenant_id',
            'mapping': {'other': 'https://example.org', 'same-host': 'https://example.org'},
        })
        setup.target_auth_scope = (1, 0, [], None)
        return setup

    def authorize(self, product, env, setup, ids):
        address = setup.test_data.get_cache('url')
        ApiAuthManager(setup).inject_cache(SimpleNamespace(cache_data={
            'v2token': 'example-token-' + address,
            **({'old_only': 'example'} if address == 'https://example.com' else {}),
        }))

    def test_route_change_removes_old_credentials_and_isolates_cases(self):
        setup = self.setup_context()
        other = self.setup_context()
        with patch.object(ApiAuthManager, 'load', side_effect=self.authorize):
            setup.ensure_execution_context()
            setup.test_data.set_cache('tenant_id', 'other')
            setup.ensure_execution_context()
        self.assertEqual(setup.test_data.get_cache('url'), 'https://example.org')
        self.assertEqual(setup.test_data.get_cache('v2token'), 'example-token-https://example.org')
        self.assertNotIn('old_only', setup.test_data.get_all())
        self.assertNotIn('v2token', other.test_data.get_all())

    def test_request_clean_uses_initialized_target_for_relative_url(self):
        setup = self.setup_context()
        setup.test_data.set_cache('tenant_id', 'other')
        request = ApiExecutionRequest(method='GET', url='/example')
        with patch.object(ApiAuthManager, 'load', side_effect=self.authorize):
            result = APIBaseTestSetup.request_data_clean(setup, request)
        self.assertEqual(result.url, 'https://example.org/example')

    def test_same_host_selector_change_also_invalidates_owned_credentials(self):
        setup = self.setup_context()
        setup.test_data.set_cache('tenant_id', 'other')
        with patch.object(ApiAuthManager, 'load', side_effect=self.authorize):
            setup.ensure_execution_context()
        setup.test_data.set_cache('tenant_id', 'same-host')
        with patch.object(ApiAuthManager, 'load') as load:
            setup.ensure_execution_context()
        load.assert_called_once()
        self.assertNotIn('v2token', setup.test_data.get_all())

    def test_failed_refresh_cannot_leave_partial_credentials_or_old_url(self):
        setup = self.setup_context()
        with patch.object(ApiAuthManager, 'load', side_effect=self.authorize):
            setup.ensure_execution_context()
        def fail(*args):
            self.authorize(*args)
            raise ConnectionError('example failure')
        with patch.object(ApiAuthManager, 'load', side_effect=fail), self.assertRaises(ConnectionError):
            setup.ensure_execution_context()
        self.assertNotIn('v2token', setup.test_data.get_all())
        self.assertNotIn('url', setup.test_data.get_all())

    def test_authorization_cannot_silently_change_routing_inputs(self):
        setup = self.setup_context()
        def change_route(*args):
            ApiAuthManager(setup).inject_cache(SimpleNamespace(cache_data={
                'tenant_id': 'other', 'v2token': 'example-token',
            }))
        with patch.object(ApiAuthManager, 'load', side_effect=change_route), self.assertRaises(AutoApiError):
            setup.ensure_execution_context()
        self.assertNotIn('tenant_id', setup.test_data.get_all())
        self.assertNotIn('v2token', setup.test_data.get_all())

    def test_unresolved_route_clears_previous_credentials(self):
        setup = self.setup_context()
        with patch.object(ApiAuthManager, 'load', side_effect=self.authorize):
            setup.ensure_execution_context()
        with patch('src.apps.auto_api.services.base.api_base_test_setup.public_base.TestTargetService.resolve',
                   side_effect=TestCenterError(TEST_TARGET_UNRESOLVED, value=('example',))), self.assertRaises(TestCenterError):
            setup.ensure_execution_context()
        self.assertNotIn('v2token', setup.test_data.get_all())
        self.assertNotIn('url', setup.test_data.get_all())

    def test_rollback_restores_shadowed_values_but_preserves_explicit_writes(self):
        setup = self.setup_context()
        setup.test_data.set_cache('baseline', {'value': 1})
        manager = ApiAuthManager(setup)
        manager.inject_cache(SimpleNamespace(cache_data={'baseline': {'value': 2}, 'manual': 'old'}))
        manager.inject_cache(SimpleNamespace(cache_data={'baseline': {'value': 3}}))
        setup.test_data.set_cache('manual', 'new')
        setup.clear_auth_injections()
        self.assertEqual(setup.test_data.get_cache('baseline'), {'value': 1})
        self.assertEqual(setup.test_data.get_cache('manual'), 'new')

    def test_authentication_context_does_not_recursively_load_authorizations(self):
        setup = self.setup_context()
        setup.skip_auth_load = True
        with patch.object(ApiAuthManager, 'load') as load:
            setup.ensure_execution_context()
        load.assert_not_called()
        self.assertEqual(setup.test_data.get_cache('url'), 'https://example.com')

    def test_case_front_inputs_are_applied_before_authorization_and_factory(self):
        setup = self.setup_context()
        case = SimpleNamespace(id=1, front_custom=[{'key': 'tenant_id', 'value': 'other'}], front_sql=[])
        runner = CaseBase(setup, case, 0)
        def check():
            self.assertEqual(setup.test_data.get_cache('url'), 'https://example.org')
            self.assertIn('v2token', setup.test_data.get_all())
        runner.case_data_factory.run_front = Mock(side_effect=check)
        with patch.object(ApiAuthManager, 'load', side_effect=self.authorize), patch.object(runner, 'init_headers'):
            runner.case_front_main()
        runner.case_data_factory.run_front.assert_called_once()

    def test_scenario_hook_can_read_auth_before_sending_request(self):
        setup = self.setup_context()
        parameter = CaseParameter.__new__(CaseParameter)
        parameter.test_setup = setup
        parameter.parameter = SimpleNamespace(front_sql=[], front_func='example')
        request = object()
        def check(code, actual):
            self.assertIn('v2token', setup.test_data.get_all())
            return actual
        with patch.object(ApiAuthManager, 'load', side_effect=self.authorize), \
                patch.object(parameter, '_CaseParameter__front_func', side_effect=check):
            self.assertIs(parameter.front_main(request), request)

    def test_both_factory_entrypoints_receive_initialized_case_cache(self):
        for cls in (CaseDataFactory, ParameterDataFactory):
            with self.subTest(cls=cls):
                setup = self.setup_context()
                with patch.object(ApiAuthManager, 'load', side_effect=self.authorize), \
                        patch('src.apps.auto_api.services.base.case_data_factory.DataFactoryCaseConfigRunner') as factory:
                    cls(setup, SimpleNamespace(id=1), configs=[]).run_front()
                self.assertIs(factory.call_args.kwargs['test_data'], setup.test_data)
                self.assertIn('v2token', setup.test_data.get_all())

    def test_code_public_values_are_available_to_factory_without_reexecution(self):
        setup = self.setup_context()
        variable = SimpleNamespace(type=ApiPublicTypeEnum.CODE.value, name='example', value='''
def variable(context):
    return {"iso_form_modules": '[{"name":"example"}]', "iso_schema_version": "1"}
''')
        with patch('src.apps.auto_api.services.base.api_base_test_setup.public_base.ApiCaseGlobalVariableService.list_public',
                   return_value=[variable]), patch.object(ApiAuthManager, 'load') as load:
            setup.init_public(1, 0)
        load.assert_not_called()
        fields = [DataFactoryField(name=key, nullable=False, platform_type='string', generator_type=13,
                                   generator_config={'value': '${{' + key + '}}'})
                  for key in ('iso_form_modules', 'iso_schema_version')]
        self.assertEqual(DataFactoryValueGenerator.build_payload(fields, test_data=setup.test_data), {
            'iso_form_modules': '[{"name":"example"}]', 'iso_schema_version': '1',
        })
