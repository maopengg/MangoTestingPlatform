from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.system.services.catalog.enum_catalog import EnumCatalogService
from src.apps.system.services.configuration.system_config import ENVIRONMENT_DISPLAY_NAMES_KEY, SYSTEM_CONFIG_REGISTRY, SystemConfigService
from src.apps.test_center.enums.environment import EnvironmentEnum


class EnvironmentDisplayTests(SimpleTestCase):
    def setUp(self):
        SystemConfigService.invalidate(ENVIRONMENT_DISPLAY_NAMES_KEY)

    def tearDown(self):
        SystemConfigService.invalidate(ENVIRONMENT_DISPLAY_NAMES_KEY)

    @patch.object(SystemConfigService, 'get', return_value={'1': '蓝环境', '5': '绿环境'})
    def test_names_override_display_only_and_share_cached_configuration(self, get):
        result = EnumCatalogService.catalog()
        self.assertEqual(dict((item['key'], item['title']) for item in result['environment_type'])[1], '蓝环境')
        self.assertEqual(EnvironmentEnum.get_value(5), '绿环境')
        self.assertEqual(EnvironmentEnum.get_value(2), '生产环境')
        self.assertEqual(EnvironmentEnum.default_obj()[1], '预发环境')
        self.assertEqual(EnvironmentEnum.PRO.value, 2)
        self.assertEqual(dict(EnvironmentEnum.choices())[1], '预发环境')
        self.assertEqual(dict((item['key'], item['title']) for item in result['environment_type_defaults']),
                         EnvironmentEnum.default_obj())
        get.assert_any_call(ENVIRONMENT_DISPLAY_NAMES_KEY, default={})
        self.assertEqual(get.call_count, 1)

    def test_validate_names(self):
        for value in [[], {'9': '新环境'}, {'1': ''}, {'1': '测试环境'}, {'1': 'x' * 33}, {'1': 123}, '{']:
            self.assertIsNotNone(SystemConfigService.validate_environment_display_names(value), value)
        self.assertIsNone(SystemConfigService.validate_environment_display_names({'1': ' 蓝环境 ', '5': '绿环境'}))
        self.assertIsNone(SystemConfigService.validate_environment_display_names({}))

    @patch.object(SystemConfigService, 'get', return_value={'5': '蓝环境', '2': '线上环境'})
    def test_environment_display_order_does_not_change_values_or_model_choices(self, get):
        result = EnumCatalogService.catalog()
        self.assertEqual([item['key'] for item in result['environment_type']], [3, 0, 1, 4, 5, 2])
        self.assertEqual([item['title'] for item in result['environment_type']], [
            '开发环境', '测试环境', '预发环境', '验收环境', '蓝环境', '线上环境',
        ])
        self.assertEqual([item['key'] for item in result['environment_type_defaults']], [3, 0, 1, 4, 5, 2])
        self.assertEqual([value for value, _name in EnvironmentEnum.choices()], list(range(6)))

    @patch.object(SystemConfigService, 'get', return_value={})
    def test_reset_and_invalidation(self, get):
        self.assertEqual(EnvironmentEnum.obj(), EnvironmentEnum.default_obj())
        cached = SystemConfigService._environment_display_names_cache
        SystemConfigService._environment_display_names_cache = (cached[0], {'1': '蓝环境'})
        self.assertEqual(EnvironmentEnum.get_value(1), '蓝环境')
        SystemConfigService.invalidate(ENVIRONMENT_DISPLAY_NAMES_KEY)
        self.assertEqual(EnvironmentEnum.get_value(1), '预发环境')

    def test_configuration_write_uses_same_validation(self):
        self.assertIsNotNone(
            SystemConfigService.validate_editable_config(ENVIRONMENT_DISPLAY_NAMES_KEY, {'1': '生产环境'}))
        config = next(item for item in SYSTEM_CONFIG_REGISTRY if item.key == ENVIRONMENT_DISPLAY_NAMES_KEY)
        self.assertEqual(config.group, 'system')
        self.assertEqual(config.default_value, {})

    @patch.object(SystemConfigService, 'get')
    def test_model_choices_and_defaults_do_not_read_configuration(self, get):
        self.assertEqual(dict(EnvironmentEnum.choices()), EnvironmentEnum.default_obj())
        self.assertEqual(EnvironmentEnum.PRO.value, 2)
        get.assert_not_called()

    @patch.object(SystemConfigService, 'get', side_effect=[{'1': ' 蓝环境 '}, {'5': '绿环境'}, {'2': ''}])
    def test_cache_expiration_and_invalid_configuration_fallback(self, get):
        self.assertEqual(EnvironmentEnum.get_value(1), '蓝环境')
        cached = SystemConfigService._environment_display_names_cache
        SystemConfigService._environment_display_names_cache = (0, cached[1])
        self.assertEqual(EnvironmentEnum.get_value(5), '绿环境')
        SystemConfigService.invalidate(ENVIRONMENT_DISPLAY_NAMES_KEY)
        self.assertEqual(EnvironmentEnum.obj(), EnvironmentEnum.default_obj())
        self.assertEqual(get.call_count, 3)

    @patch.object(SystemConfigService, 'get', return_value={'1': '蓝环境'})
    def test_group_notice_report_uses_custom_name(self, get):
        from src.apps.task_center.services.scheduling.task_group_execution import ScheduledTaskGroupExecutionService
        now = datetime(2026, 10, 12, 18, 0)
        execution = SimpleNamespace(
            id=1, task_group_name='回归', test_env=1, planned_at=now,
            create_time=now, finished_at=now,
            project_product=SimpleNamespace(name='示例产品', project=SimpleNamespace(name='示例项目')),
        )
        report = ScheduledTaskGroupExecutionService._build_report(execution, [])
        self.assertEqual(report.test_environment, '蓝环境')
