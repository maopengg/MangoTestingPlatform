"""Bind confirmation to request inputs, not preview-generated context."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.system.services.runtime_kv import RuntimeKV
from src.interfaces.mcp import common
from src.interfaces.mcp.tests.test_dangerous_confirmation import ConfirmationStoreFixture
from src.interfaces.mcp.tools.data_factory import template
from src.interfaces.mcp.tools.data_factory.helpers import _data_factory_template_run_target


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(func):
            self.tools[func.__name__] = func
            return func
        return register


class FactoryConfirmationContextTests(SimpleTestCase):
    def setUp(self):
        registry = ToolRegistry()
        template.register_template_tools(registry)
        self.preview = registry.tools['preview_run_data_factory_template_impact']
        self.execute = registry.tools['execute_data_factory_template']
        self.args = {
            'template_id': 42, 'test_env': 0,
            'context': {'actor': 'fixture-actor', 'nested': {'values': ['original']}},
            'overrides': {'name': {'generator_type': 1, 'generator_config': {'value': 'fixture'}}},
        }
        self.store = ConfirmationStoreFixture()
        for patcher in (
            patch.object(common, 'current_user', return_value=SimpleNamespace(id=7)),
            patch.object(RuntimeKV, 'namespace', return_value=self.store),
            patch.object(template, '_selected_test_env', return_value=0),
            patch.object(template, '_data_factory_result_with_cache_keys', side_effect=lambda value, _: value),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        query = patch.object(template.DataFactoryQuerySelector, 'data_factory_template')
        query.start().return_value.get.return_value = SimpleNamespace(id=42, name='Fixture task')
        self.addCleanup(query.stop)
        preview = patch.object(template.DataFactoryPreviewService, 'preview_template', side_effect=self.generate_preview)
        preview.start()
        self.addCleanup(preview.stop)
        runner = patch.object(template.DataFactoryRunner, 'debug_run_template', return_value={'execution_id': 1})
        self.runner = runner.start()
        self.addCleanup(runner.stop)

    @staticmethod
    def generate_preview(**kwargs):
        context = kwargs['context']
        context['generated_root'] = {'id': 'preview-only-id'}
        context['nested']['values'].append('preview-only')
        kwargs['overrides']['name']['generator_config']['value'] = 'preview-only'
        return {'can_debug_run': True, 'context': context}

    def test_target_uses_original_request_inputs(self):
        expected = _data_factory_template_run_target(**self.args)
        response = self.preview(**deepcopy(self.args))
        self.assertTrue(response['success'])
        self.assertEqual(response['data']['target_id'], expected)
        self.assertIn('generated_root', response['data']['impact']['context'])

    def test_preview_does_not_mutate_nested_request_inputs(self):
        original = deepcopy(self.args)
        self.preview(**self.args)
        self.assertEqual(self.args, original)

    def test_separate_wire_requests_can_consume_fresh_confirmation(self):
        preview = self.preview(**deepcopy(self.args))['data']
        result = self.execute(**deepcopy(self.args), preview_token=preview['preview_token'],
                              confirm_text=preview['confirm_text'])
        self.assertTrue(result['success'], result)
        self.runner.assert_called_once_with(template_id=42, overrides=self.args['overrides'],
                                            context=self.args['context'], test_object_id=None, test_env=0)
        replay = self.execute(**deepcopy(self.args), preview_token=preview['preview_token'],
                              confirm_text=preview['confirm_text'])
        self.assertEqual(replay['error_code'], 'PREVIEW_EXPIRED')
        self.runner.assert_called_once()

    def test_changed_request_still_requires_new_preview(self):
        preview = self.preview(**deepcopy(self.args))['data']
        changed = deepcopy(self.args)
        changed['context']['actor'] = 'different-actor'
        result = self.execute(**changed, preview_token=preview['preview_token'], confirm_text=preview['confirm_text'])
        self.assertEqual(result['error_code'], 'PREVIEW_EXPIRED')
        self.runner.assert_not_called()
