from contextlib import ExitStack
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from mangotools.exceptions import MangoToolsError

from src.apps.data_factory.models import DataFactoryField
from src.apps.data_factory.services.generator import DataFactoryValueGenerator
from src.apps.data_factory.services.runner import DataFactoryRunner
from src.apps.data_factory.services.runtime_cache import DataFactoryRuntimeCache
from src.common.testing import ObtainTestData


class RuntimeContextTests(SimpleTestCase):
    def setUp(self):
        self.context = {'qa_array_fixture_cat': 10, 'qa_array_fixture_form_id': 20,
                        'qa_array_fixture_template_id': 30, 'qa_array_fixture_name': 'AUTO_array_fixture'}
        self.fields = [DataFactoryField(name=name, nullable=False, platform_type=kind, generator_type=13,
                                       generator_config={'value': '${{' + key + '}}'})
                       for name, kind, key in [
                           ('category_id', 'integer', 'qa_array_fixture_cat'),
                           ('form_id', 'integer', 'qa_array_fixture_form_id'),
                           ('template_id', 'integer', 'qa_array_fixture_template_id'),
                           ('contract_name', 'string', 'qa_array_fixture_name'),
                           ('contract_number', 'string', 'qa_array_fixture_name'),
                       ]]
        self.cache = ObtainTestData()
        self.cache.set_cache('qa_array_fixture_cat', -1)
        self.cache.set_data_factory_cache('existing.id', 77)
        self.expected = {'category_id': 10, 'form_id': 20, 'template_id': 30,
                         'contract_name': 'AUTO_array_fixture', 'contract_number': 'AUTO_array_fixture'}

    def assert_cache_restored(self):
        self.assertEqual(self.cache.get_cache('qa_array_fixture_cat'), -1)
        self.assertFalse(self.cache.has_cache('qa_array_fixture_form_id'))
        self.assertEqual(self.cache.get_cache('existing.id'), 77)

    def test_scope_resolves_values_and_preserves_types(self):
        original = deepcopy(self.context)
        with DataFactoryRuntimeCache.bind_context(self.cache, self.context):
            self.assertEqual(DataFactoryValueGenerator.build_payload(self.fields, test_data=self.cache), self.expected)
        self.assert_cache_restored()
        self.assertEqual(self.context, original)

    def test_nested_objects_and_false_values_are_not_discarded(self):
        with DataFactoryRuntimeCache.bind_context(self.cache, {'fixture': {'id': 123}, 'zero': 0,
                                                               'flag': False, 'none': None,
                                                               '__executor': {'user_id': 999}}):
            self.assertEqual(self.cache.replace('${{fixture.id}}'), 123)
            self.assertEqual(self.cache.get_cache('zero'), 0)
            self.assertIs(self.cache.get_cache('flag'), False)
            self.assertTrue(self.cache.has_cache('none'))
            self.assertIsNone(self.cache.get_cache('none'))
            self.assertFalse(self.cache.has_cache('__executor.user_id'))
        self.assertFalse(self.cache.has_cache('fixture.id'))

    def test_exception_restores_cache_and_later_request_cannot_reuse_values(self):
        with self.assertRaises(MangoToolsError):
            with DataFactoryRuntimeCache.bind_context(self.cache, self.context):
                self.cache.replace('${{missing_fixture_value}}')
        self.assert_cache_restored()
        with self.assertRaises(MangoToolsError):
            self.cache.replace('${{qa_array_fixture_template_id}}')

    def test_nested_scopes_restore_outer_values(self):
        with DataFactoryRuntimeCache.bind_context(self.cache, self.context):
            with DataFactoryRuntimeCache.bind_context(self.cache, {'qa_array_fixture_cat': 99}):
                self.assertEqual(self.cache.get_cache('qa_array_fixture_cat'), 99)
            self.assertEqual(self.cache.get_cache('qa_array_fixture_cat'), 10)
        self.assert_cache_restored()

    def runner_patches(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        entity = SimpleNamespace(id=1, name='订单', table_name='fixture', primary_key='id', unique_key='',
                                 create_type=2, schema_name='', datafactoryfield_set=Mock())
        entity.datafactoryfield_set.all.return_value.order_by.return_value = self.fields
        template = SimpleNamespace(id=425, name='订单草稿', entity=entity, project_product_id=3,
                                   project_product=Mock(), module=Mock(), field_overrides={},
                                   output_config=[], post_insert_updates=[])
        database = SimpleNamespace(id=1, database_name='test', db_type=1, host='example.com', port=3306)
        stack.enter_context(patch.object(DataFactoryRunner, 'get_template', return_value=template))
        stack.enter_context(patch.object(DataFactoryRuntimeCache, 'build_test_data', return_value=self.cache))
        stack.enter_context(patch('src.apps.data_factory.services.runner_parts.preview.'
                                  'DataFactoryDatasourceResolver.resolve_entity_binding'))
        stack.enter_context(patch('src.apps.data_factory.services.runner_parts.preview.'
                                  'DataFactoryDatasourceResolver.require_binding_permission'))
        stack.enter_context(patch('src.apps.data_factory.services.runner_parts.preview.'
                                  'DatasourceTargetService.resolve', return_value=database))
        stack.enter_context(patch.object(DataFactoryRunner, 'get_template_items', return_value=[]))
        stack.enter_context(patch.object(DataFactoryRunner, 'preview_post_insert_updates', return_value=[]))
        stack.enter_context(patch.object(DataFactoryRunner, 'build_dependency_tree', return_value={}))
        return stack, template

    def test_environment_preview_consumes_context_without_persisting_it(self):
        self.runner_patches()
        result = DataFactoryRunner.preview_template(425, context=deepcopy(self.context), test_object_id=1, test_env=0)
        self.assertEqual(result['payload'], self.expected)
        self.assertEqual(result['missing_fields'], [])
        self.assertTrue(result['can_debug_run'])
        self.assert_cache_restored()

    def test_execution_impact_preview_accepts_original_expressions_and_dynamic_context(self):
        from src.interfaces.mcp.tools.data_factory.template import register_template_tools
        stack, template = self.runner_patches()
        tools = {}
        class Capture:
            def tool(self):
                def register(func):
                    tools[func.__name__] = func
                    return func
                return register
        register_template_tools(Capture())
        selector = stack.enter_context(patch('src.interfaces.mcp.tools.data_factory.template.'
                                             'DataFactoryQuerySelector.data_factory_template'))
        selector.return_value.get.return_value = template
        stack.enter_context(patch('src.interfaces.mcp.tools.data_factory.template._selected_test_env', return_value=0))
        stack.enter_context(patch('src.interfaces.mcp.tools.data_factory.template.'
                                  '_data_factory_result_with_cache_keys', side_effect=lambda result, _: result))
        confirm = stack.enter_context(patch('src.interfaces.mcp.tools.data_factory.template.'
                                             'create_dangerous_action_preview',
                                             side_effect=lambda _action, _target, _text, impact: impact))
        result = tools['preview_run_data_factory_template_impact'](
            425, context=deepcopy(self.context), test_object_id=1, test_env=0,
        )
        self.assertTrue(result['success'])
        self.assertTrue(result['data']['can_execute'])
        self.assertEqual(result['data']['payload'], self.expected)
        confirm.assert_called_once()
        self.assert_cache_restored()

    def test_case_binding_mcp_preview_reads_the_same_dynamic_context(self):
        from src.interfaces.mcp.tools.data_factory.case_config import register_case_config_tools
        stack, template = self.runner_patches()
        tools = {}
        class Capture:
            def tool(self):
                def register(func):
                    tools[func.__name__] = func
                    return func
                return register
        register_case_config_tools(Capture())
        selector = stack.enter_context(patch('src.interfaces.mcp.tools.data_factory.helpers.'
                                             'DataFactoryQuerySelector.data_factory_template'))
        selector.return_value.get.return_value = template
        stack.enter_context(patch('src.interfaces.mcp.tools.data_factory.helpers._selected_test_env', return_value=0))
        stack.enter_context(patch('src.interfaces.mcp.tools.data_factory.helpers.'
                                  '_data_factory_result_with_cache_keys', side_effect=lambda result, _: result))
        result = tools['preview_data_factory_case_config'](
            425, context=deepcopy(self.context), test_object_id=1, test_env=0,
        )
        self.assertTrue(result['success'])
        self.assertTrue(result['data']['can_debug_run'])
        self.assertEqual(result['data']['payload'], self.expected)
        self.assert_cache_restored()

    def test_execution_failure_restores_context_and_keeps_cleanup_path(self):
        from src.apps.data_factory.enums import DataFactoryExecutionStatusEnum
        stack, _ = self.runner_patches()
        execution = SimpleNamespace(id=1, execution_no='DF_TEST', save=Mock(), context={})
        stack.enter_context(patch.object(DataFactoryRunner, 'require_template_entities_available'))
        stack.enter_context(patch('src.apps.data_factory.services.runner_parts.execution.'
                                  'DataFactoryExecution.objects.create', return_value=execution))
        def create(*args, test_data=None, **kwargs):
            return DataFactoryValueGenerator.build_payload(self.fields, test_data=test_data)
        stack.enter_context(patch.object(DataFactoryRunner, 'create_by_template', side_effect=create))
        cleanup = stack.enter_context(patch.object(DataFactoryRunner, 'cleanup_failed_execution'))
        context = dict(self.context)
        context.pop('qa_array_fixture_name')
        with self.assertRaises(MangoToolsError):
            DataFactoryRunner.run_template(425, source_type=4, context=context, test_object_id=1, test_env=0)
        self.assertEqual(execution.status, DataFactoryExecutionStatusEnum.FAIL.value)
        cleanup.assert_called_once()
        self.assert_cache_restored()

    def test_debug_and_case_execution_share_the_same_context_binding(self):
        stack, _ = self.runner_patches()
        execution = SimpleNamespace(id=1, execution_no='DF_TEST', save=Mock(), context={})
        stack.enter_context(patch.object(DataFactoryRunner, 'require_template_entities_available'))
        stack.enter_context(patch('src.apps.data_factory.services.runner_parts.execution.'
                                  'DataFactoryExecution.objects.create', return_value=execution))
        def create(*args, test_data=None, **kwargs):
            return DataFactoryValueGenerator.build_payload(self.fields, test_data=test_data)
        stack.enter_context(patch.object(DataFactoryRunner, 'create_by_template', side_effect=create))
        stack.enter_context(patch.object(DataFactoryRunner, 'create_template_items', return_value=[]))
        stack.enter_context(patch.object(DataFactoryRunner, 'execute_post_insert_updates', return_value=[]))
        stack.enter_context(patch.object(DataFactoryRunner, 'resolve_execution_cleanup_status', return_value=1))
        stack.enter_context(patch.object(DataFactoryRunner, 'sync_execution_cleanup_todo'))
        for run, extra in [(DataFactoryRunner.debug_run_template, {}),
                           (DataFactoryRunner.run_template, {'source_type': 4})]:
            with self.subTest(entry=run.__name__):
                result = run(425, context=deepcopy(self.context), test_object_id=1, test_env=0, **extra)
                self.assertEqual(result['data'], self.expected)
                self.assert_cache_restored()
