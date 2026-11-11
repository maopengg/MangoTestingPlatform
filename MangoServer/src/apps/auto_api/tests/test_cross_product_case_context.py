from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.auto_api.enums import ApiPublicTypeEnum
from src.apps.auto_api.exceptions import AutoApiError, API_CASE_STEP_PROJECT_MISMATCH
from src.apps.auto_api.services.api_case.step import ApiCaseStepService
from src.apps.auto_api.services.base.api_base_test_setup.public_base import PublicBase
from src.apps.auto_api.services.base.api_base_test_setup.auth_manager import ApiAuthManager
from src.apps.auto_api.services.base.case_base import CaseBase
from src.apps.auto_api.services.test_case.step_debug import ApiCaseStepDebugContextService


class CrossProductCaseContextTests(SimpleTestCase):
    def make_setup(self):
        with patch('src.apps.auto_api.services.base.api_base_test_setup.base_request.CacheDataValue.get_cache_value',
                   return_value=30):
            return PublicBase()

    @staticmethod
    def target(env, product, automation_type):
        return SimpleNamespace(id=product, project_product_id=product, environment=env,
                               value=f'https://p{product}.example.com', target_config={})

    @staticmethod
    def public(product, env, ids):
        return [SimpleNamespace(type=ApiPublicTypeEnum.CUSTOM.value, key='product_value', value=str(product)),
                SimpleNamespace(type=ApiPublicTypeEnum.CUSTOM.value, key=f'only_{product}', value='private')]

    @staticmethod
    def authorize(product, env, setup, ids):
        ApiAuthManager(setup).inject_cache(SimpleNamespace(cache_data={f'auth_{product}': 'token',
                                                                     'token': str(product)}))

    @patch('src.apps.auto_api.services.base.api_base_test_setup.public_base.func_test_object_value', side_effect=target)
    @patch('src.apps.auto_api.services.base.api_base_test_setup.public_base.ApiCaseGlobalVariableService.list_public', side_effect=public)
    @patch.object(ApiAuthManager, 'load', side_effect=authorize)
    def test_a_b_a_selects_own_domain_variables_and_auth_and_keeps_step_outputs(self, auth, public, target):
        setup = self.make_setup()
        setup.test_data.set_cache('case_input', 'shared')
        for product in (1, 2, 1):
            setup.init_test_object(product, 5)
            setup.init_public(product, 5)
            setup.ensure_execution_context()
            data = setup.test_data.get_all()
            other = 3 - product
            self.assertEqual(data['url'], f'https://p{product}.example.com')
            self.assertEqual(data['product_value'], str(product))
            self.assertEqual(data['token'], str(product))
            self.assertNotIn(f'only_{other}', data)
            self.assertNotIn(f'auth_{other}', data)
            self.assertEqual(data['case_input'], 'shared')
            setup.test_data.set_cache('step_output', 'shared-result')
        self.assertEqual(setup.test_data.get_cache('step_output'), 'shared-result')

    @patch('src.apps.auto_api.services.base.api_base_test_setup.public_base.func_test_object_value', side_effect=target)
    def test_failed_target_lookup_cannot_reuse_previous_target_or_url(self, target):
        setup = self.make_setup()
        setup.init_test_object(1, 5)
        target.side_effect = RuntimeError('unavailable')
        with self.assertRaises(RuntimeError):
            setup.init_test_object(2, 5)
        self.assertIsNone(setup.test_object)
        self.assertIsNone(setup.is_test_object)
        self.assertNotIn('url', setup.test_data.get_all())

    @patch('src.apps.auto_api.services.base.api_base_test_setup.public_base.func_test_object_value', side_effect=target)
    @patch('src.apps.auto_api.services.base.api_base_test_setup.public_base.ApiCaseGlobalVariableService.list_public')
    def test_code_variables_and_partial_initialization_are_scoped(self, public, target):
        setup = self.make_setup()
        setup.init_test_object(1, 5)
        public.return_value = [SimpleNamespace(type=ApiPublicTypeEnum.CODE.value, name='fixture',
            value='def variable(context):\n    return {"code_owned": "A"}')]
        setup.init_public(1, 5)
        self.assertIn('code_owned', setup.product_cache_keys())
        setup.init_test_object(2, 5)
        self.assertNotIn('code_owned', setup.test_data.get_all())
        public.return_value = [*self.public(2, 5, []), SimpleNamespace(type=ApiPublicTypeEnum.CODE.value,
            name='invalid', value='def variable(context):\n    raise RuntimeError("fixture")')]
        with self.assertRaises(AutoApiError):
            setup.init_public(2, 5)
        self.assertNotIn('product_value', setup.test_data.get_all())
        self.assertNotIn('only_2', setup.test_data.get_all())
        self.assertNotIn('url', setup.test_data.get_all())
        self.assertIsNone(setup.target_auth_scope)

    @patch('src.apps.auto_api.services.base.api_base_test_setup.public_base.func_test_object_value', side_effect=target)
    def test_switch_revokes_owned_auth_even_after_a_step_overrides_its_value(self, target):
        setup = self.make_setup()
        setup.init_test_object(1, 5)
        self.authorize(1, 5, setup, [])
        setup.test_data.set_cache('token', 'step-overrode-token')
        setup.init_test_object(2, 5)
        self.assertNotIn('token', setup.test_data.get_all())
        self.assertNotIn('auth_1', setup.test_data.get_all())

    @patch('src.apps.auto_api.services.base.api_base_test_setup.public_base.func_test_object_value', side_effect=target)
    @patch('src.apps.auto_api.services.base.api_base_test_setup.public_base.ApiCaseGlobalVariableService.list_public', side_effect=public)
    def test_case_cleanup_returns_to_the_case_product(self, public, target):
        setup = self.make_setup()
        setup.init_test_object(2, 5)
        setup.init_public(2, 5)
        base = CaseBase.__new__(CaseBase)
        base.test_setup, base.test_env = setup, 5
        base.api_case = SimpleNamespace(project_product_id=1, front_public=[], front_auth_config=[], posterior_sql=[])
        base.case_data_factory = Mock()
        base.case_posterior_main()
        self.assertEqual(setup.test_object.project_product_id, 1)
        self.assertNotIn('only_2', setup.test_data.get_all())
        base.case_data_factory.cleanup.assert_called_once()


class CrossProductStepDebugTests(SimpleTestCase):
    @patch('src.apps.auto_api.services.test_case.step_debug.ApiCaseDetailed.objects')
    @patch.object(ApiCaseStepDebugContextService, 'validate_snapshot_chain')
    def test_debug_restores_business_outputs_but_not_product_credentials(self, chain, objects):
        case = SimpleNamespace(parametrize=[], project_product_id=1)
        steps = [SimpleNamespace(id=i, case=case, api_info=SimpleNamespace(name='fixture', project_product_id=i))
                 for i in (1, 2)]
        objects.select_related.return_value.filter.return_value.order_by.return_value = steps
        snapshot = SimpleNamespace(snapshot_id='snapshot-1', data_factory_cache_data={},
            product_cache_keys=['url', 'token'], cache_data={'url': 'https://example.com', 'token': 'private', 'order_id': 'shared'})
        chain.return_value = [snapshot]
        state = ApiCaseStepDebugContextService.prepare(case_id=1, case_detailed_id=2,
                                                       test_env=5, user_id=1, context_id='fixture')
        self.assertEqual(state.cache_data, {'order_id': 'shared'})
        snapshot.product_cache_keys = None
        with self.assertRaises(AutoApiError):
            ApiCaseStepDebugContextService.prepare(case_id=1, case_detailed_id=2,
                                                   test_env=5, user_id=1, context_id='fixture')


class CrossProductStepBoundaryTests(SimpleTestCase):
    @patch('src.apps.auto_api.api.views.api_case_detailed.ApiInfo.objects')
    @patch.object(ApiCaseStepService, 'create_step_with_default_parameter')
    def test_http_create_checks_target_interface_scope_before_writing(self, create, infos):
        from inspect import getclosurevars, unwrap
        from src.apps.auto_api.api.views.api_case_detailed import ApiCaseDetailedCRUD
        view = ApiCaseDetailedCRUD()
        view.get_case_for_update = Mock(return_value=SimpleNamespace(id=1))
        view.has_instance_data_scope_permission = Mock(return_value=False)
        request = SimpleNamespace(data={'case': 1, 'api_info': 2})
        unwrap(getclosurevars(ApiCaseDetailedCRUD.post).nonlocals['func'])(view, request)
        view.has_instance_data_scope_permission.assert_called_once_with(
            request, infos.get.return_value)
        create.assert_not_called()

    @patch('src.apps.auto_api.services.api_case.step.ApiInfo.objects')
    @patch('src.apps.auto_api.services.api_case.step.ApiCase.objects')
    def test_same_project_is_allowed_and_other_project_is_rejected(self, cases, infos):
        cases.filter.return_value.values_list.return_value.first.return_value = 7
        infos.filter.return_value.values_list.return_value.first.return_value = 7
        ApiCaseStepService.validate_project(1, 2)
        infos.filter.return_value.values_list.return_value.first.return_value = 8
        with self.assertRaises(AutoApiError):
            ApiCaseStepService.validate_project(1, 2)
        infos.filter.return_value.values_list.return_value.first.return_value = None
        with self.assertRaises(AutoApiError):
            ApiCaseStepService.validate_project(1, 2)

    @patch.object(ApiCaseStepService, 'validate_project', side_effect=AutoApiError(API_CASE_STEP_PROJECT_MISMATCH))
    @patch.object(ApiCaseStepService, 'resolve_api_runtime')
    def test_create_rejects_before_resolving_or_writing_step(self, runtime, guard):
        with self.assertRaises(AutoApiError):
            ApiCaseStepService.create_step_with_default_parameter.__wrapped__(
                ApiCaseStepService, case_id=1, api_info_id=2, case_sort=0)
        runtime.assert_not_called()
