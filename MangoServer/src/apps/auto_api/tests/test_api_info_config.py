from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from src.apps.auto_api.models import ApiInfo
from src.apps.auto_api.services.api_info.config import ApiInfoConfigService


class ToolRegistry:

    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(func):
            self.tools[func.__name__] = func
            return func

        return register


class ApiInfoConfigServiceTests(SimpleTestCase):

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
