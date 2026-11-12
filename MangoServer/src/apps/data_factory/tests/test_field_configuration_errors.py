"""字段生成配置错误属于业务拒绝，不记录系统异常或泄露原始输入。"""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.data_factory.api.views.field import DataFactoryFieldViews
from src.apps.data_factory.enums import DataFactoryGeneratorTypeEnum
from src.apps.data_factory.exceptions import (
    DataFactoryError, DATA_FACTORY_FIELD_DEPENDENCY_ENTITY_REQUIRED,
    DATA_FACTORY_FIELD_GENERATOR_CONFIG_INVALID,
)
from src.apps.data_factory.services.assets.field import DataFactoryFieldService as Fields
from src.interfaces.mcp.server import _mcp_failure_result


class FieldConfigurationErrorTests(SimpleTestCase):
    def field(self, config):
        return {'name': 'AUTO_owner_id', 'platform_type': 'integer',
                'generator_type': DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
                'generator_config': config}

    def test_missing_dependency_has_field_and_action_without_pydantic_error(self):
        for config in ({'field': 'id'}, {}, {'dependency_entity_id': None}, {'dependency_entity_id': ''}):
            with self.subTest(config=config), self.assertRaises(DataFactoryError) as caught:
                Fields.normalize_field_data(self.field(config))
            self.assertEqual(caught.exception.code, DATA_FACTORY_FIELD_DEPENDENCY_ENTITY_REQUIRED.code)
            self.assertIn('AUTO_owner_id', caught.exception.msg)
            self.assertIn('dependency_entity_id', caught.exception.msg)
            self.assertIn('请选择依赖实体后保存', caught.exception.msg)
            self.assertNotIn('input_value', caught.exception.msg)
            self.assertNotIn('pydantic', caught.exception.msg)

    def test_invalid_dependency_type_does_not_echo_sensitive_input(self):
        with self.assertRaises(DataFactoryError) as caught:
            Fields.normalize_field_data(self.field({'dependency_entity_id': 'AUTO_SECRET_VALUE'}))
        self.assertEqual(caught.exception.code, DATA_FACTORY_FIELD_GENERATOR_CONFIG_INVALID.code)
        self.assertIn('dependency_entity_id', caught.exception.msg)
        self.assertIn('整数', caught.exception.msg)
        self.assertNotIn('AUTO_SECRET_VALUE', caught.exception.msg)
        self.assertNotIn('input_value', caught.exception.msg)

    def test_non_object_configuration_is_business_error(self):
        for config in ([], False, 1, 'AUTO_SECRET_VALUE'):
            with self.subTest(type=type(config)), self.assertRaises(DataFactoryError) as caught:
                Fields.normalize_field_data(self.field(config))
            self.assertEqual(caught.exception.code, DATA_FACTORY_FIELD_GENERATOR_CONFIG_INVALID.code)
            self.assertNotIn('AUTO_SECRET_VALUE', caught.exception.msg)

    def test_valid_dependency_still_normalizes_as_before(self):
        field = self.field({'dependency_entity_id': 12, 'field': 'id'})
        Fields.normalize_field_data(field)
        self.assertEqual(field['generator_config'], {'dependency_entity_id': 12, 'field': 'id'})

    def test_invalid_batch_never_saves_or_deletes_fields(self):
        with patch('src.apps.data_factory.services.assets.field.DataFactoryField.objects') as objects, \
                patch('src.apps.data_factory.services.assets.field.save_model') as save, \
                self.assertRaises(DataFactoryError):
            objects.filter.return_value.first.return_value = None
            Fields.save_schema_fields.__wrapped__(Fields, SimpleNamespace(id=1), [self.field({'field': 'id'})])
        save.assert_not_called()
        objects.filter.return_value.exclude.assert_not_called()

    def test_preview_keeps_other_valid_fields_and_shows_business_reason(self):
        result = Fields.preview_values([self.field({'field': 'id'}), {
            'name': 'AUTO_label', 'platform_type': 'string',
            'generator_type': DataFactoryGeneratorTypeEnum.FIXED.value,
            'generator_config': {'value': 'AUTO_VALID'},
        }])
        self.assertFalse(result['fields'][0]['valid'])
        self.assertIn('缺少依赖实体 ID', result['fields'][0]['message'])
        self.assertNotIn('input_value', result['fields'][0]['message'])
        self.assertEqual(result['payload'], {'AUTO_label': 'AUTO_VALID'})

    def test_preview_does_not_silently_turn_invalid_empty_array_into_object(self):
        result = Fields.preview_values([self.field([])])
        self.assertFalse(result['fields'][0]['valid'])
        self.assertIn('JSON 对象', result['fields'][0]['message'])

    def test_http_batch_returns_business_error_without_system_record(self):
        request = SimpleNamespace(data={'entity_id': 1, 'fields': [self.field({'field': 'id'})]}, user={'id': 4})
        save = Fields.save_schema_fields.__wrapped__
        with patch('src.apps.data_factory.api.views.field.DataFactoryEntity.objects') as entities, \
                patch('src.apps.data_factory.api.views.field.DataFactoryFieldCRUD.has_data_scope_permission', return_value=True), \
                patch.object(Fields, 'save_schema_fields', side_effect=lambda *args: save(Fields, *args)), \
                patch('src.apps.data_factory.services.assets.field.DataFactoryField.objects') as objects, \
                patch('src.common.decorators.error_response.report_system_error') as report:
            entities.get.return_value = SimpleNamespace(id=1)
            objects.filter.return_value.first.return_value = None
            response = DataFactoryFieldViews().batch_save(request)
        self.assertEqual(response.data['code'], DATA_FACTORY_FIELD_DEPENDENCY_ENTITY_REQUIRED.code)
        self.assertIn('AUTO_owner_id', response.data['msg'])
        report.assert_not_called()

    def test_mcp_boundary_does_not_report_configuration_error_as_system_exception(self):
        with self.assertRaises(DataFactoryError) as caught:
            Fields.normalize_field_data(self.field({'field': 'id'}))
        with patch('src.interfaces.mcp.server._report_mcp_system_error') as report:
            response, status = _mcp_failure_result(caught.exception, 'tool:create_data_factory_entity',
                                                  'unexpected', 'MCP_TOOL_EXCEPTION', {})
        self.assertFalse(response['success'])
        self.assertEqual(response['error_code'], str(DATA_FACTORY_FIELD_DEPENDENCY_ENTITY_REQUIRED.code))
        self.assertLess(status, 500)
        report.assert_not_called()

    def test_unexpected_internal_errors_are_not_swallowed_as_bad_input(self):
        with patch('src.apps.data_factory.services.assets.field.validate_data_factory_generator_config',
                   side_effect=RuntimeError('AUTO_INTERNAL_FAILURE')), self.assertRaises(RuntimeError):
            Fields.normalize_field_data(self.field({'dependency_entity_id': 12}))
