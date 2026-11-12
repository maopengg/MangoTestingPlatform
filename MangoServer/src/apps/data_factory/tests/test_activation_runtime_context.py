from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from mangotools.exceptions import MangoToolsError

from src.apps.data_factory.enums import DataFactoryOperationTypeEnum, DataFactoryTemplateUsageScopeEnum
from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.models import DataFactoryField
from src.apps.data_factory.services.execution.generator import DataFactoryValueGenerator
from src.apps.data_factory.services.execution.runner import DataFactoryRunner
from src.apps.data_factory.services.assets.template import DataFactoryTemplateService
from src.common.testing import ObtainTestData


class ActivationRuntimeContextTests(SimpleTestCase):
    def preview(self, fields, activation=True, internal=False, context=None, template_id=292, name='根'):
        entity = SimpleNamespace(id=7, name='实体', table_name='fixture', primary_key='id',
                                 unique_key='', create_type=DataFactoryOperationTypeEnum.SQL.value,
                                 schema_name='', datafactoryfield_set=Mock())
        entity.datafactoryfield_set.all.return_value.order_by.return_value = fields
        template = SimpleNamespace(id=template_id, name=name, entity=entity, field_overrides={},
                                   output_config=[], usage_scope=DataFactoryTemplateUsageScopeEnum.INTERNAL.value
            if internal else DataFactoryTemplateUsageScopeEnum.CASE.value)
        database = SimpleNamespace(id=1, database_name='test', db_type=1, host='example.com', port=3306)
        cache = Mock()
        cache.replace.return_value = None
        with (
            patch(
                'src.apps.data_factory.services.execution.parts.preview.DataFactoryDatasourceResolver.resolve_entity_binding'),
            patch(
                'src.apps.data_factory.services.execution.parts.preview.DataFactoryDatasourceResolver.require_binding_permission'),
            patch('src.apps.data_factory.services.execution.parts.preview.DatasourceTargetService.resolve',
                  return_value=database),
            patch.object(DataFactoryRunner, 'build_effective_fields', return_value=fields),
            patch.object(DataFactoryRunner, 'build_dependency_tree', return_value={}),
        ):
            return DataFactoryRunner.preview_by_template(
                template, {}, context if context is not None else {}, 1, set(),
                test_data=cache, activation_validation=activation,
            ), cache

    def test_activation_defers_case_variables_without_executing_them(self):
        result, cache = self.preview([
            DataFactoryField(name='attribute_key', nullable=False, generator_type=13,
                             generator_config={'value': '${{number_fixture_key}}'}),
            DataFactoryField(name='module_id', nullable=False, generator_type=13,
                             generator_config={'value': '${{number_fixture_module_id}}'}),
        ])
        self.assertTrue(result['configuration_valid'])
        self.assertTrue(result['runtime_context_required'])
        self.assertFalse(result['can_debug_run'])
        self.assertEqual(result['payload'], {
            'attribute_key': '${{根.attribute_key}}', 'module_id': '${{根.module_id}}',
        })
        self.assertEqual(result['missing_fields'], [])
        cache.replace.assert_not_called()

    def test_activation_propagates_deferred_dependency_across_multiple_consumers(self):
        context = {}
        upstream, _ = self.preview([
            DataFactoryField(name='id', nullable=False, generator_type=13,
                             generator_config={'value': '${{number_fixture_id}}'}),
            DataFactoryField(name='category_name', nullable=False, generator_type=13,
                             generator_config={'value': '${{str_fixture_name}}'}),
        ], context=context)
        dependency_template = SimpleNamespace(id=292, name='根', entity=SimpleNamespace(
            id=7, name='实体', table_name='fixture'))
        fields = [DataFactoryField(name=target, nullable=False, generator_type=11,
                                   generator_config={'template_id': 292, 'dependency_entity_id': 7,
                                                     'field': source, 'strategy': 'reuse_or_create'})
                  for target, source in [('category_id', 'id'), ('category_name', 'category_name')]]
        with patch.object(DataFactoryRunner, 'get_dependency_template', return_value=dependency_template):
            for template_id in [293, 294]:
                result, _ = self.preview(fields, context=context, template_id=template_id,
                                         name=f'子模板{template_id}')
                self.assertTrue(result['configuration_valid'])
                self.assertTrue(result['runtime_context_required'])
                self.assertFalse(result['can_debug_run'])
                self.assertEqual(result['missing_fields'], [])
                self.assertTrue(all(field['deferred'] for field in result['fields']))
                self.assertEqual(result['payload']['category_id'], '${{根.id}}')
                self.assertTrue(all(dependency['runtime_context_required']
                                    for dependency in result['dependencies']))
        self.assertTrue(upstream['configuration_valid'])

    def test_reused_dependency_does_not_hide_real_empty_value(self):
        dependency_template = SimpleNamespace(id=292, name='根', entity=SimpleNamespace(
            id=7, name='实体', table_name='fixture'))
        field = DataFactoryField(name='category_id', nullable=False, generator_type=11,
                                 generator_config={'template_id': 292, 'dependency_entity_id': 7,
                                                   'field': 'id', 'strategy': 'reuse_or_create'})
        with patch.object(DataFactoryRunner, 'get_dependency_template', return_value=dependency_template):
            result, _ = self.preview([field], context={'根': {'id': None}}, template_id=293)
            self.assertFalse(result['configuration_valid'])
            self.assertEqual(result['missing_fields'][0]['field'], 'category_id')
            result, _ = self.preview([field], context={'根': {'id': 0}}, template_id=293)
            self.assertTrue(result['configuration_valid'])
            self.assertFalse(result['runtime_context_required'])
            self.assertEqual(result['payload']['category_id'], 0)

    def test_environment_preview_does_not_defer_empty_dependency(self):
        dependency_template = SimpleNamespace(id=292, name='根', entity=SimpleNamespace(
            id=7, name='实体', table_name='fixture'))
        field = DataFactoryField(name='category_id', nullable=False, generator_type=11,
                                 generator_config={'template_id': 292, 'dependency_entity_id': 7,
                                                   'field': 'id', 'strategy': 'reuse_or_create'})
        with patch.object(DataFactoryRunner, 'get_dependency_template', return_value=dependency_template):
            result, _ = self.preview([field], activation=False, context={'根': {}}, template_id=293)
        self.assertFalse(result['configuration_valid'])
        self.assertEqual(result['missing_fields'][0]['field'], 'category_id')

    def test_environment_preview_still_rejects_unresolved_required_variable(self):
        result, cache = self.preview([
            DataFactoryField(name='module_id', nullable=False, generator_type=13,
                             generator_config={'value': '${{number_fixture_module_id}}'}),
        ], activation=False)
        self.assertFalse(result['configuration_valid'])
        self.assertFalse(result['can_debug_run'])
        self.assertEqual(result['missing_fields'][0]['field'], 'module_id')
        cache.replace.assert_called_once()

    def test_empty_function_is_not_deferred(self):
        result, _ = self.preview([
            DataFactoryField(name='module_id', nullable=False, generator_type=13, generator_config={}),
        ])
        self.assertFalse(result['configuration_valid'])
        self.assertEqual(result['missing_fields'][0]['field'], 'module_id')

    def test_static_missing_value_is_not_hidden(self):
        result, _ = self.preview([
            DataFactoryField(name='module_id', nullable=False, generator_type=1,
                             generator_config={'value': None}),
        ])
        self.assertFalse(result['configuration_valid'])
        self.assertFalse(result['runtime_context_required'])

    def test_internal_leaf_defers_parent_but_public_root_does_not(self):
        field = DataFactoryField(name='previous_id', nullable=False, generator_type=11,
                                 generator_config={'source_node': 'root', 'source_field': 'id'})
        result, _ = self.preview([field], internal=True)
        self.assertTrue(result['configuration_valid'])
        self.assertTrue(result['runtime_context_required'])
        result, _ = self.preview([field], internal=False)
        self.assertFalse(result['configuration_valid'])

    def test_status_service_accepts_static_qualification_not_debug_permission(self):
        template = SimpleNamespace(id=292, name='根', field_overrides={}, output_config=[],
                                   config_status=0, save=Mock())
        with (
            patch.object(DataFactoryRunner, 'require_template_entities_available'),
            patch.object(DataFactoryTemplateService, 'activation_environments', return_value=[0]),
            patch('src.apps.data_factory.services.assets.template.DataFactoryPreviewService.preview_template',
                  return_value={'configuration_valid': True, 'can_debug_run': False,
                                'runtime_context_required': True}) as preview,
        ):
            result = DataFactoryTemplateService.validate_activation(template)
        self.assertEqual(template.config_status, 1)
        self.assertEqual(result['checked_environments'], [0])
        self.assertTrue(preview.call_args.kwargs['activation_validation'])

    def test_runtime_uses_case_cache_and_does_not_accept_missing_variables(self):
        fields = [DataFactoryField(name=name, nullable=False, platform_type='string', generator_type=13,
                                   generator_config={'value': '${{number_fixture_key}}'})
                  for name in ['attribute_key', 'attribute_code']]
        cache = ObtainTestData()
        cache.set_cache('number_fixture_key', 'custom_1_AUTO_fixture')
        payload = DataFactoryValueGenerator.build_payload(fields, test_data=cache)
        self.assertEqual(payload, {'attribute_key': 'custom_1_AUTO_fixture',
                                   'attribute_code': 'custom_1_AUTO_fixture'})
        with self.assertRaises(MangoToolsError):
            DataFactoryValueGenerator.build_payload(fields, test_data=ObtainTestData())

    def test_activation_error_includes_child_template_path_and_field(self):
        template = SimpleNamespace(id=292, name='根', field_overrides={}, output_config=[],
                                   config_status=0, save=Mock())
        with (
            patch.object(DataFactoryRunner, 'require_template_entities_available'),
            patch.object(DataFactoryTemplateService, 'activation_environments', return_value=[0]),
            patch('src.apps.data_factory.services.assets.template.DataFactoryPreviewService.preview_template',
                  return_value={'configuration_valid': False, 'missing_fields': [], 'dependencies': [],
                                'all_missing_fields': [{'path': '根 / 分类绑定', 'field': 'category_id'}]}),
            self.assertRaises(DataFactoryError) as error,
        ):
            DataFactoryTemplateService.validate_activation(template)
        self.assertIn('根 / 分类绑定 / category_id', str(error.exception))

    def test_child_qualification_does_not_claim_debug_readiness(self):
        child = SimpleNamespace(id=293, name='叶子')
        item = SimpleNamespace(id=1, name='较早叶子', sort=0, child_template_id=293,
                               child_template=child, field_overrides={})
        result = {'configuration_valid': True, 'can_debug_run': False,
                  'runtime_context_required': True, 'dependency_tree': {}}
        with (
            patch.object(DataFactoryRunner, 'get_template_items', return_value=[item]),
            patch.object(DataFactoryRunner, 'prepare_scene_item_overrides', return_value={}),
            patch.object(DataFactoryRunner, 'preview_by_template', return_value={
                'configuration_valid': True, 'can_debug_run': False,
                'runtime_context_required': True, 'dependency_tree': {},
            }) as preview,
        ):
            result = DataFactoryRunner.preview_template_items(
                SimpleNamespace(), result, {}, {}, 1, test_data=Mock(), activation_validation=True,
            )
        self.assertTrue(result['configuration_valid'])
        self.assertFalse(result['can_debug_run'])
        self.assertTrue(preview.call_args.kwargs['activation_validation'])
