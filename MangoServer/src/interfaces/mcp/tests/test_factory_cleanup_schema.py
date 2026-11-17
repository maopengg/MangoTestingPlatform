import re
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from django.test import SimpleTestCase
from fastmcp import Client, FastMCP
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.server.auth import AccessToken

from src.interfaces.mcp.authentication import TOKEN_VERIFIER
from src.interfaces.mcp.server import mcp_asgi_app
from src.interfaces.mcp.tools.data_factory.template import register_template_tools
from src.apps.data_factory.schemas.cleanup_resource import EsCleanupRule


class FactoryCleanupSchemaTests(SimpleTestCase):
    async def test_authenticated_http_root_and_domain_expose_typed_cleanup_resources(self):
        access = AccessToken(token='test-factory-schema-key', client_id='schema-test', subject='7', scopes=[],
                             claims={'user_id': 7, 'is_super_admin': True})
        for domain in (None, 'data-factory'):
            app = mcp_asgi_app(domain)

            def client_factory(**kwargs):
                kwargs.pop('follow_redirects', None)
                return httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                         base_url='https://mcp.example.com', follow_redirects=True, **kwargs)

            transport = StreamableHttpTransport('https://mcp.example.com/',
                                                headers={'Authorization': 'Bearer test-factory-schema-key'},
                                                httpx_client_factory=client_factory)
            with self.subTest(domain=domain), \
                    patch.object(TOKEN_VERIFIER, 'verify_token', new=AsyncMock(return_value=access)), \
                    patch('src.interfaces.mcp.common.get_http_headers', return_value={}), \
                    patch('src.interfaces.mcp.authentication.bearer_token', return_value=None):
                async with app.router.lifespan_context(app):
                    async with Client(transport) as client:
                        tools = {tool.name: tool for tool in await client.list_tools()}
                for name in ('create_data_factory_template', 'update_data_factory_template'):
                    schema = tools[name].inputSchema
                    self.assertIn('cleanup_resources', schema['properties'])
                    resource = schema['properties']['cleanup_resources']
                    array = next(value for value in resource.get('anyOf', [resource]) if value.get('type') == 'array')
                    rule = array['items']
                    if '$ref' in rule:
                        rule = schema['$defs'][rule['$ref'].rsplit('/', 1)[-1]]
                    self.assertIn('document_id_field', rule['properties'])
                    self.assertIsNone(rule['properties']['document_id_field']['default'])
                    self.assertFalse(rule['additionalProperties'])
                    pattern = rule['properties']['index_template']['pattern']
                    self.assertEqual(pattern, EsCleanupRule.model_json_schema()['properties']['index_template']['pattern'])
                    self.assertIsNotNone(re.fullmatch(pattern, '{tenant}'))
                    self.assertIsNone(re.fullmatch(pattern, '{tenant}*'))

    async def test_real_mcp_call_accepts_mapping_and_preserves_omission_semantics(self):
        server = FastMCP('factory-cleanup-input-test')
        register_template_tools(server)
        with patch('src.interfaces.mcp.tools.data_factory.template.mcp_current_user_id', return_value=7), \
                patch('src.interfaces.mcp.tools.data_factory.template._cache_keys_for_template', return_value=[]), \
                patch('src.interfaces.mcp.tools.data_factory.template.DataFactoryQuerySelector.data_factory_template') as query, \
                patch('src.interfaces.mcp.tools.data_factory.template.DataFactoryTemplateMutationService.update',
                      return_value={'id': 31}) as update:
            query.return_value.get.return_value = SimpleNamespace(config_status=1)
            async with Client(server) as client:
                response = await client.call_tool('update_data_factory_template', {
                    'template_id': 31, 'cleanup_resources': [{
                        'datasource_alias_id': 8, 'index_template': 'example_template_{tenant}', 'document_id_field': 'id',
                    }],
                })
                self.assertFalse(response.is_error)
                rules = update.call_args.args[1]['cleanup_resources']
                self.assertEqual(rules[0]['document_id_field'], 'id')
                self.assertEqual(rules[0]['mode'], 'verify')
                response = await client.call_tool('update_data_factory_template', {
                    'template_id': 31, 'cleanup_resources': [{
                        'datasource_alias_id': 8, 'index_template': '{tenant}', 'document_id_field': 'id',
                    }],
                })
                self.assertFalse(response.is_error)
                self.assertEqual(update.call_args.args[1]['cleanup_resources'][0]['index_template'], '{tenant}')
                update.reset_mock()
                for index in ('{tenant}*', '{tenant}/_search', '{tenant}{tenant}', '{unknown}'):
                    response = await client.call_tool('update_data_factory_template', {
                        'template_id': 31, 'cleanup_resources': [{'datasource_alias_id': 8, 'index_template': index}],
                    }, raise_on_error=False)
                    self.assertTrue(response.is_error)
                update.assert_not_called()
                await client.call_tool('update_data_factory_template', {'template_id': 31, 'description': 'AUTO示例'})
                self.assertNotIn('cleanup_resources', update.call_args.args[1])
                await client.call_tool('update_data_factory_template', {'template_id': 31, 'cleanup_resources': []})
                self.assertEqual(update.call_args.args[1]['cleanup_resources'], [])
