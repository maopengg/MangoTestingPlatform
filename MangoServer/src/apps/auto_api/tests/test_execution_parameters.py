from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.http import QueryDict
from django.test import SimpleTestCase

from src.apps.auto_api.api.serializers.api_info_execution import ApiInfoExecutionQuery
from src.apps.auto_api.api.views.api_info import ApiInfoViews, ApiInfoCRUD
from src.apps.auto_api.services.api_info.execution_parameters import ApiInfoExecutionParametersService
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.services.permission import PermissionMenuService


class ExecutionParametersTests(SimpleTestCase):
    def test_detects_unique_request_variables_without_exposing_values_or_postprocessing(self):
        result = ApiInfoExecutionParametersService.collect({
            'url': 'https://example.com/${{item_id}}',
            'headers': {'Authorization': 'private-prefix ${{token}}'},
            'body_config': {'body_text': '{"id":"${{item_id}}", "value":"${{body}}"}'},
            'params': [{'key': '${{key}}', 'value': '${{body}} ${{}}'}],
            'posterior_func': 'print("${{not_a_request_variable}}")',
        })
        self.assertEqual(result, ['item_id', 'key', 'body'])
        self.assertNotIn('private', str(result))

    def test_detection_uses_the_selected_revision(self):
        with patch('src.apps.auto_api.services.api_info.execution_parameters.ApiInfoRuntimeService.resolve_payload',
                   return_value=({'url': '${{frozen}}', 'headers': {}}, None)) as resolve:
            self.assertEqual(ApiInfoExecutionParametersService.names(1, revision_id=7), ['frozen'])
        resolve.assert_called_once_with(1, revision_id=7, release_id=None)

    def test_inherited_headers_are_not_queried_or_prompted(self):
        with patch('src.apps.auto_api.services.api_info.execution_parameters.ApiInfoRuntimeService.resolve_payload',
                   return_value=({'headers': None}, None)), patch(
            'src.apps.auto_api.models.ApiHeaders.objects.filter',
        ) as headers:
            self.assertEqual(ApiInfoExecutionParametersService.names(1), [])
        headers.assert_not_called()

    def test_nested_protocol_headers_are_excluded_but_body_fields_are_preserved(self):
        result = ApiInfoExecutionParametersService.collect({
            'protocol_config': {'type': 'http', 'config': {
                'headers': {'Authorization': '${{header_token}}'},
                'url': 'https://example.com/${{path}}',
                'body_config': {'body': {'headers': '${{business_value}}'}},
            }},
            'mcp_binding': {'mcp_config': {
                'headers': {'Authorization': '${{mcp_token}}'},
                'body_config': {'body': {'value': '${{argument}}'}},
            }},
        })
        self.assertEqual(result, ['argument', 'path', 'business_value'])

    def test_entered_values_override_global_initialization_only_for_this_run(self):
        from src.apps.auto_api.services.base.api_base_test_setup import APIBaseTestSetup
        from src.common.testing import ObtainTestData
        setup = APIBaseTestSetup.__new__(APIBaseTestSetup)
        setup.current_api_info_id = None
        setup.test_data = ObtainTestData()
        setup.init_test_object = MagicMock()
        setup.init_public = lambda *args: setup.test_data.set_cache('token', 'global-value')
        setup._apply_mcp_binding = MagicMock()
        setup._apply_grpc_binding = MagicMock()
        setup.request_data_clean = lambda value: setup.test_data.replace('${{token}}')
        setup.http = MagicMock(return_value=SimpleNamespace())
        setup.api_request(1, 0, api_info=SimpleNamespace(id=1, name='Example', project_product_id=2),
                          request_model=object(), runtime_parameters={'token': 'entered-value'}, apply_api_info_posterior=False)
        setup.http.assert_called_once_with('entered-value', 2)

    def test_post_runtime_values_remain_typed_and_test_environment_zero_is_valid(self):
        query = ApiInfoExecutionQuery(data={'id': 1, 'test_env': 0, 'runtime_parameters': {'count': 0, 'body': {}}})
        self.assertTrue(query.is_valid(), query.errors)
        self.assertEqual(query.validated_data['runtime_parameters'], {'count': 0, 'body': {}})
        self.assertFalse(ApiInfoExecutionQuery(data={'id': 1, 'test_env': 0, 'runtime_parameters': []}).is_valid())

    def test_parameter_endpoint_requires_debug_or_execute_permission(self):
        view = ApiInfoViews()
        view.action = 'get_execution_parameters'
        request = SimpleNamespace(method='GET', path='/api/api/info/execution/parameters', data={},
                                  query_params=QueryDict('id=1'), user=SimpleNamespace(user_obj=SimpleNamespace(id=9)))
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False):
            for key, expected in (('api.info:debug', True), ('api.info:execute', True), ('api.info', False)):
                with patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={key}):
                    self.assertEqual(MenuActionPermission().has_permission(request, view), expected)

    def test_denied_scope_neither_reads_variables_nor_executes(self):
        for action, method in (('get_execution_parameters', 'GET'), ('get_api_info_run', 'POST')):
            request = SimpleNamespace(method=method, query_params=QueryDict('id=1'),
                                      data={'id': 1, 'test_env': 0}, user={'id': 9})
            with patch('src.apps.auto_api.api.views.api_info.ApiInfo.objects.filter') as api, patch.object(
                ApiInfoCRUD, 'has_instance_data_scope_permission', return_value=False,
            ), patch.object(ApiInfoExecutionParametersService, 'names') as names, patch(
                'src.apps.auto_api.api.views.api_info.TestApiInfo',
            ) as runner:
                api.return_value.first.return_value = SimpleNamespace(id=1)
                response = getattr(ApiInfoViews(), action)(request)
            self.assertNotEqual(response.data['code'], 0)
            names.assert_not_called()
            runner.assert_not_called()

    def test_post_injects_runtime_parameters_and_legacy_get_is_still_supported(self):
        for method in ('GET', 'POST'):
            payload = {'id': 1, 'test_env': 0, 'runtime_parameters': {'body': {'value': 'example'}}}
            request = SimpleNamespace(method=method, data=payload, query_params=QueryDict('id=1&test_env=0'), user={'id': 9})
            with patch('src.apps.auto_api.api.views.api_info.ApiInfo.objects.filter'), patch.object(
                ApiInfoCRUD, 'has_instance_data_scope_permission', return_value=True,
            ), patch('src.apps.auto_api.api.views.api_info.TestApiInfo') as runner, patch(
                'src.apps.auto_api.api.views.api_info.ExecutionResultService',
            ) as results:
                runner.return_value.api_info_run.return_value = {'status': 1}
                results.save_result.return_value = SimpleNamespace(id=7)
                results.serialize_run_response.return_value = {'id': 7}
                response = ApiInfoViews().get_api_info_run(request)
            self.assertEqual(response.data['data']['id'], 7)
            kwargs = runner.return_value.api_info_run.call_args.kwargs
            self.assertEqual(kwargs.get('runtime_parameters'), payload['runtime_parameters'] if method == 'POST' else None)
