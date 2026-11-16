from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from src.apps.auto_api.models import ApiInfo
from src.apps.auto_api.services.api_info.config import ApiInfoConfigService
from src.apps.auto_api.exceptions import AutoApiError


class ToolRegistry:

    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(func):
            self.tools[func.__name__] = func
            return func

        return register


class ApiInfoConfigServiceTests(SimpleTestCase):

    def test_path_variables_accept_platform_expressions_without_rewriting_names(self):
        for url in (
            '/categories', '/categories/${{CATEGORY_ID}}',
            '/categories/${{categoryId}}/items/${{item.id}}',
            '/files/prefix-${{文件名}}.json', '/items/${{random_number(1, 10)}}',
            '/items/${{lookup(${{tenant_id}})}}',
            '/items/${{lookup({"id": 1})}}',
            '/items/${{lookup("}")}}', '/files/%7Bexample%7D',
        ):
            with self.subTest(url=url):
                self.assertIsNone(ApiInfoConfigService.validate_url_path(url))

    def test_path_variables_reject_source_routes_and_incomplete_placeholders(self):
        for url in (
            '/categories/{CATEGORY_ID}', '/categories/${CATEGORY_ID}',
            '/categories/{{CATEGORY_ID}}', '/items/${{}}', '/items/${{  }}',
            '/items/${{id}', '/items/${{id}}}', '/items/${{id',
            '/items/id}', '/items/${{id}}/{other}', '/items/${{lookup("}")}',
        ):
            for protocol in ('http', 'sse', 'websocket'):
                with self.subTest(url=url, protocol=protocol):
                    error = ApiInfoConfigService.validate_url_path(url, protocol)
                    self.assertIn('变量格式不正确', error)
                    self.assertIn('/categories/${{CATEGORY_ID}}', error)
                    self.assertIn('区分大小写', error)

    def test_http_create_and_edit_reject_bad_path_before_persisting(self):
        from src.apps.auto_api.api.views.api_info import ApiInfoCRUD
        from src.apps.auto_api.services.api_info.mutation import ApiInfoMutationService

        invalid_url = '/categories/{CATEGORY_ID}'
        expected = ApiInfoConfigService.validate_url_path(invalid_url)
        payload = {'project_product': 1, 'module': 2, 'name': '分类查询',
                   'url': invalid_url, 'method': 0, 'protocol_type': 'http'}
        with patch.object(ApiInfoMutationService, 'create_validated') as create:
            with self.assertRaises(AutoApiError) as raised:
                ApiInfoCRUD.inside_post(payload)
            self.assertEqual(raised.exception.msg, expected)
        create.assert_not_called()
        with (
            patch('src.apps.auto_api.services.api_info.mutation.ApiInfo.objects.get',
                  return_value=SimpleNamespace(id=12, project_product_id=1, module_id=2)),
            patch('src.apps.auto_api.services.api_info.mutation.ApiInfoRuntimeService.resolve_runtime',
                  return_value=SimpleNamespace(url='/categories', method=0, protocol_type='http', body_type='none')),
            patch.object(ApiInfoMutationService, 'update_validated') as update,
        ):
            with self.assertRaises(AutoApiError) as raised:
                ApiInfoCRUD.inside_put(12, {'url': invalid_url})
            self.assertEqual(raised.exception.msg, expected)
        update.assert_not_called()

    def test_recording_import_cannot_bypass_path_variable_validation(self):
        from src.apps.auto_api.services.api_info.mutation import ApiInfoMutationService

        with patch('src.apps.auto_api.services.api_info.mutation.save_model') as save:
            with self.assertRaises(AutoApiError) as raised:
                ApiInfoMutationService.create.__wrapped__(
                    ApiInfoMutationService, {'url': '/categories/{CATEGORY_ID}'}, source='recording',
                )
            self.assertEqual(raised.exception.code, 31234)
            self.assertIn('/categories/${{CATEGORY_ID}}', raised.exception.msg)
        save.assert_not_called()

    def setUp(self):
        self.existing = SimpleNamespace(id=10, name='上传附件')
        self.runtime = SimpleNamespace(
            id=10,
            url='/resources',
            method=1,
            protocol_type='http',
            body_type='multipart',
        )

    def find_duplicate(self, body_type):
        queryset = MagicMock()
        queryset.only.return_value = [self.existing]
        with (
            patch(
                'src.apps.auto_api.services.api_info.config.ProjectProduct.objects.only',
            ) as project_product_only,
            patch(
                'src.apps.auto_api.services.api_info.config.ApiInfo.objects.filter',
                return_value=queryset,
            ),
            patch(
                'src.apps.auto_api.services.api_info.config.ApiInfoRuntimeService.resolve_runtime',
                return_value=self.runtime,
            ),
        ):
            project_product_only.return_value.get.return_value = SimpleNamespace(api_client_type=1)
            return ApiInfoConfigService.find_duplicate_api_config(
                project_product_id=1,
                module_id=2,
                url='/resources',
                method=1,
                protocol_type='http',
                body_type=body_type,
            )

    def test_same_request_identity_with_different_body_type_is_allowed(self):
        self.assertIsNone(self.find_duplicate('json'))

    def test_same_request_identity_with_same_body_type_is_duplicate(self):
        self.assertEqual(self.find_duplicate('multipart'), self.runtime)

    def test_api_info_default_posterior_fields_are_valid(self):
        api_info = ApiInfo(
            project_product_id=1,
            module_id=2,
            name='默认后置配置',
            url='/default-posterior-config',
        )

        api_info.clean_fields(exclude=['project_product', 'module'])

        self.assertEqual(api_info.posterior_json_path, [])
        self.assertEqual(api_info.posterior_re, [])
        self.assertIsNone(api_info.posterior_func)


class ApiInfoMcpToolTests(SimpleTestCase):

    def setUp(self):
        from src.interfaces.mcp.tools.api.api_info import register_api_info_tools

        self.registry = ToolRegistry()
        register_api_info_tools(self.registry)

    def test_mcp_create_and_edit_return_same_friendly_path_validation(self):
        module = 'src.interfaces.mcp.tools.api.api_info'
        invalid_url = '/categories/{CATEGORY_ID}'
        expected = ApiInfoConfigService.validate_url_path(invalid_url)
        with patch(module + '.ApiInfoMutationService.create_definition') as create:
            result = self.registry.tools['create_api_info'](
                project_product_id=1, module_id=2, name='分类查询', url=invalid_url, method=0,
            )
            self.assertFalse(result['success'])
            self.assertEqual(result['message'], expected)
            self.assertEqual(result['error_code'], 'INVALID_API_INFO_URL')
        create.assert_not_called()
        with (
            patch(module + '._require_published_api_info_modify_confirmation', return_value=None),
            patch(module + '.ApiInfoRuntimeService.resolve_runtime',
                  return_value=SimpleNamespace(protocol_type='http')),
            patch(module + '.ApiInfoMutationService.update_definition') as update,
        ):
            result = self.registry.tools['update_api_info'](api_info_id=12, url=invalid_url)
            self.assertFalse(result['success'])
            self.assertEqual(result['message'], expected)
            self.assertEqual(result['error_code'], 'INVALID_API_INFO_URL')
        update.assert_not_called()

    def test_mcp_curl_import_rejects_source_route_placeholder(self):
        result = self.registry.tools['create_api_info_from_curl'](
            project_product_id=1, module_id=2, name='分类查询',
            curl_command="curl 'https://example.com/categories/{CATEGORY_ID}'",
        )
        self.assertFalse(result['success'])
        self.assertEqual(result['error_code'], 'INVALID_API_INFO_URL')
        self.assertIn('/categories/${{CATEGORY_ID}}', result['message'])

    def test_update_api_info_saves_expression_headers_through_existing_service(self):
        module = 'src.interfaces.mcp.tools.api.api_info'
        runtime = SimpleNamespace(protocol_type='sse', url='/chat', method=1, body_type='json')
        headers = {'authorization': '${{token}}', 'x-unbox-supported-renderers': 'collection@1'}
        with patch(module + '._require_published_api_info_modify_confirmation', return_value=None), \
                patch(module + '.ApiInfoRuntimeService.resolve_runtime', return_value=runtime), \
                patch(module + '.ApiInfoConfigService.validate_url_path', return_value=None), \
                patch(module + '.ApiInfoConfigService.find_duplicate_api_config', return_value=None), \
                patch(module + '.ApiQuerySelector.api_info') as query, \
                patch(module + '.mcp_current_user_id', return_value=4), \
                patch(module + '.ApiInfoMutationService.update_definition') as update, \
                patch(module + '._api_info_mutation_result', return_value={'id': 12}):
            query.return_value.get.return_value = SimpleNamespace(project_product_id=1, module_id=2)
            result = self.registry.tools['update_api_info'](api_info_id=12, headers=headers)
        self.assertTrue(result['success'])
        self.assertEqual(update.call_args.args, (12, {'id': 12, 'headers': headers}))

    def test_header_update_still_requires_published_asset_confirmation(self):
        module = 'src.interfaces.mcp.tools.api.api_info'
        rejection = {'success': False, 'message': 'confirmation required'}
        with patch(module + '._require_published_api_info_modify_confirmation', return_value=rejection), \
                patch(module + '.ApiInfoMutationService.update_definition') as update:
            self.assertEqual(self.registry.tools['update_api_info'](api_info_id=12, headers={}), rejection)
        update.assert_not_called()

    def test_create_api_info_rejects_unknown_body_type(self):
        result = self.registry.tools['create_api_info'](
            project_product_id=1,
            module_id=2,
            name='上传附件',
            url='/resources',
            method=1,
            body_type='yaml',
        )

        self.assertFalse(result['success'])
        self.assertEqual(result['error_code'], 'BODY_TYPE_NOT_FOUND')

    @patch('src.interfaces.mcp.tools.api.api_info.mcp_current_user_id', return_value=4)
    @patch(
        'src.interfaces.mcp.tools.api.api_info._api_info_mutation_result',
        return_value={'id': 12, 'name': '消息通道'},
    )
    @patch('src.interfaces.mcp.tools.api.api_info.ApiInfoMutationService.create_definition')
    @patch('src.interfaces.mcp.tools.api.api_info.ApiInfoConfigService.find_duplicate_api_config')
    def test_create_websocket_api_info_uses_json_body_type(
            self,
            find_duplicate,
            create_definition,
            _mutation_result,
            _current_user_id,
    ):
        find_duplicate.return_value = None

        result = self.registry.tools['create_api_info'](
            project_product_id=1,
            module_id=2,
            name='消息通道',
            url='/socket',
            method=9,
            protocol_type='websocket',
        )

        self.assertTrue(result['success'])
        self.assertEqual(find_duplicate.call_args.kwargs['body_type'], 'json')
        self.assertEqual(create_definition.call_args.args[0]['body_type'], 'json')
        self.assertEqual(create_definition.call_args.kwargs['operator_id'], 4)
