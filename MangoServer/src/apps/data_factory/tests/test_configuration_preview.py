from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.data_factory.api.views.case_config import DataFactoryCaseConfigViews
from src.apps.data_factory.api.views.template import DataFactoryTemplateViews
from src.apps.data_factory.models import DataFactoryField
from src.apps.data_factory.services.configuration_preview import DataFactoryConfigurationPreviewService as Preview
from src.apps.data_factory.services.runner import DataFactoryRunner


class ConfigurationPreviewTests(SimpleTestCase):
    def preview(self, fields, children=None):
        manager = Mock()
        manager.all.return_value.order_by.return_value = fields
        entity = SimpleNamespace(id=1, name='实体', table_name='sample', datafactoryfield_set=manager)
        template = SimpleNamespace(id=1, name='模板', entity=entity, field_overrides={}, post_insert_updates=[])
        with (
            patch.object(DataFactoryRunner, 'get_template', return_value=template),
            patch.object(DataFactoryRunner, 'get_template_items',
                         side_effect=lambda node: children or [] if node.id == 1 else []),
            patch.object(DataFactoryRunner, 'preview_post_insert_updates', return_value=[]),
            patch(
                'src.apps.data_factory.services.datasource.DataFactoryDatasourceResolver.resolve_entity_binding') as resolve,
            patch('src.apps.data_factory.services.runtime_cache.DataFactoryRuntimeCache.build_test_data') as runtime,
        ):
            result = Preview.preview(1)
        resolve.assert_not_called()
        runtime.assert_not_called()
        return result

    def test_fixed_and_random_values_without_environment(self):
        result = self.preview([
            DataFactoryField(name='name', generator_type=1, generator_config={'value': 'AUTO示例'}),
            DataFactoryField(name='score', generator_type=3, generator_config={'min': 10, 'max': 20}),
        ])
        self.assertEqual(result['payload']['name'], 'AUTO示例')
        self.assertTrue(10 <= result['payload']['score'] <= 20)
        self.assertFalse(result['can_debug_run'])

    def test_autoincrement_and_functions_never_generate_fake_values(self):
        result = self.preview([
            DataFactoryField(name='id', autoincrement=True, generator_type=3),
            DataFactoryField(name='method', generator_type=13, generator_config={'value': '${{method()}}'}),
            DataFactoryField(name='tenant', generator_type=1, generator_config={'value': '${{tenant_id}}'}),
        ])
        self.assertEqual(result['payload'], {})
        self.assertEqual([field['display_value'] for field in result['fields']],
                         ['插入后获取', '执行时获取', '执行时获取'])

    def test_invalid_rule_is_visible_without_environment_error(self):
        result = self.preview([DataFactoryField(name='score', generator_type=3,
                                                generator_config={'min': 20, 'max': 10})])
        self.assertFalse(result['fields'][0]['valid'])
        self.assertEqual(len(result['missing_fields']), 1)

    def test_associated_template_fields_and_node_references_are_previewed_offline(self):
        manager = Mock()
        manager.all.return_value.order_by.return_value = [
            DataFactoryField(name='parent_id', generator_type=11,
                             generator_config={'source_node': 'root', 'source_field': 'id'}),
        ]
        entity = SimpleNamespace(id=2, name='子表', table_name='child', datafactoryfield_set=manager)
        child = SimpleNamespace(id=2, name='子模板', entity=entity, field_overrides={}, post_insert_updates=[])
        item = SimpleNamespace(id=3, name='关联项', child_template_id=2, child_template=child,
                               field_overrides={})
        result = self.preview([], [item])
        self.assertEqual(result['items'][0]['fields'][0]['display_value'], '执行时获取')
        self.assertEqual(result['dependency_tree']['children'][0]['scene_item_id'], 3)

    def test_template_configuration_endpoint_never_calls_environment_preview(self):
        request = SimpleNamespace(data={'template_id': 1, 'preview_mode': 'configuration',
                                        'test_env': 2, 'items': [], 'output_config': []})
        with (
            patch.object(Preview, 'preview', return_value={'preview_mode': 'configuration'}) as preview,
            patch('src.apps.data_factory.api.views.template.DataFactoryPreviewService.preview_template') as environment,
        ):
            response = DataFactoryTemplateViews().preview(request)
        environment.assert_not_called()
        preview.assert_called_once_with(1, None, None, output_config=[], post_insert_updates=None, items=[])
        self.assertEqual(response.data['data']['preview_mode'], 'configuration')

    def test_case_configuration_endpoint_never_calls_environment_preview(self):
        request = SimpleNamespace(data={'template_id': 1, 'preview_mode': 'configuration', 'test_env': 2})
        with (
            patch.object(Preview, 'preview', return_value={}) as preview,
            patch(
                'src.apps.data_factory.api.views.case_config.DataFactoryPreviewService.preview_template') as environment,
        ):
            DataFactoryCaseConfigViews().preview(request)
        environment.assert_not_called()
        preview.assert_called_once_with(1, None, None)

    def test_unsaved_configuration_does_not_modify_template(self):
        manager = Mock()
        manager.all.return_value.order_by.return_value = []
        template = SimpleNamespace(id=1, name='模板', field_overrides={}, output_config=[],
                                   post_insert_updates=[], entity=SimpleNamespace(
                id=1, name='实体', table_name='sample', datafactoryfield_set=manager))
        with (
            patch.object(DataFactoryRunner, 'get_template', return_value=template),
            patch.object(DataFactoryRunner, 'get_template_items') as stored_items,
            patch.object(DataFactoryRunner, 'preview_post_insert_updates', return_value=[]),
        ):
            Preview.preview(1, items=[], output_config=[{'field': 'id', 'key': 'result'}],
                            post_insert_updates=[{'target_node': 'root'}])
        stored_items.assert_not_called()
        self.assertEqual(template.output_config, [])
        self.assertEqual(template.post_insert_updates, [])
