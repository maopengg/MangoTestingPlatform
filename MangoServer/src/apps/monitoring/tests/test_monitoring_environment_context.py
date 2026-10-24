from types import SimpleNamespace
from unittest import TestCase, mock

from mangotools.enums import StatusEnum

from src.apps.monitoring.services.base_monitor import MonitorBase
from src.apps.monitoring.services.environment_context import MonitoringEnvironmentContextService
from src.apps.test_center.enums.environment import EnvironmentEnum


class MonitoringEnvironmentContextServiceTest(TestCase):
    def test_empty_environment_does_not_build_context(self):
        task = SimpleNamespace(test_env=None, project_product_id=8)

        self.assertIsNone(MonitoringEnvironmentContextService.build(task))

    @mock.patch.object(MonitoringEnvironmentContextService, '_database_configs')
    @mock.patch.object(MonitoringEnvironmentContextService, '_domains')
    def test_build_exposes_preferred_domain_and_databases(self, domains_mock, databases_mock):
        domains_mock.return_value = {
            'common': 'https://common.example.com',
            'api': 'https://api.example.com',
        }
        databases_mock.return_value = {'主库': {'host': 'db.example.com'}}

        result = MonitoringEnvironmentContextService.build(
            SimpleNamespace(test_env=EnvironmentEnum.TEST.value, project_product_id=8)
        )

        self.assertEqual(result['domain'], 'https://api.example.com')
        self.assertEqual(result['test_env_name'], '测试环境')
        self.assertEqual(result['databases']['主库']['host'], 'db.example.com')

    @mock.patch(
        'src.apps.monitoring.services.environment_context.DataFactoryDatasourceBinding.objects.select_related'
    )
    def test_database_configs_are_keyed_by_logical_alias(self, select_related_mock):
        alias = SimpleNamespace(id=3, name='主库')
        database = SimpleNamespace(
            id=5,
            display_name='测试 MySQL',
            source_category=0,
            db_type=0,
            host='db.example.com',
            port=3306,
            name='demo',
            user='tester',
            password='secret',
            extra_config={},
        )
        binding = SimpleNamespace(
            datasource_alias=alias,
            database=database,
            db_c_status=StatusEnum.SUCCESS.value,
            db_rud_status=StatusEnum.FAIL.value,
        )
        queryset = select_related_mock.return_value
        queryset.filter.return_value.filter.return_value.annotate.return_value.order_by.return_value = [
            binding
        ]

        result = MonitoringEnvironmentContextService._database_configs(8, 0)

        self.assertEqual(result['主库']['db_type_name'], 'MySQL')
        self.assertNotIn('password', result['主库'])
        self.assertTrue(result['主库']['can_query'])
        self.assertFalse(result['主库']['can_write'])


class MonitorBaseEnvironmentContextTest(TestCase):
    @mock.patch('src.apps.test_center.services.database_connection.DatabaseConnectionFactory.create')
    @mock.patch(
        'src.apps.data_factory.services.datasource.DataFactoryDatasourceResolver.resolve_binding_by_env'
    )
    def test_database_connection_keeps_platform_permissions(self, resolve_mock, create_mock):
        database = SimpleNamespace(id=5)
        resolve_mock.return_value = SimpleNamespace(database=database)
        monitor = MonitorBase()
        monitor.test_env = 0
        monitor._project_product_id = 8
        monitor.database_configs = {
            '主库': {
                'alias_id': 3,
                'can_query': True,
                'can_write': False,
            }
        }

        result = monitor.get_database_connection('主库')

        self.assertIs(result, create_mock.return_value)
        resolve_mock.assert_called_once_with(3, 8, 0)
        create_mock.assert_called_once_with(database, allow_query=True, allow_write=False)

    @mock.patch(
        'src.apps.monitoring.services.base_monitor.MonitoringEnvironmentContextService.build'
    )
    @mock.patch('src.apps.monitoring.models.MonitoringTask.objects.only')
    def test_selected_environment_is_available_from_self(self, only_mock, build_mock):
        task = SimpleNamespace(id=12, project_product_id=8, test_env=0)
        only_mock.return_value.filter.return_value.first.return_value = task
        build_mock.return_value = {
            'test_env': 0,
            'test_env_name': '测试环境',
            'domain': 'https://api.example.com',
            'domains': {'api': 'https://api.example.com'},
            'databases': {'主库': {'host': 'db.example.com'}},
        }

        monitor = MonitorBase(task_id=12)

        self.assertEqual(monitor.domain, 'https://api.example.com')
        self.assertEqual(monitor.get_database_config('主库')['host'], 'db.example.com')
        self.assertIs(monitor.databases, monitor.database_configs)

    @mock.patch(
        'src.apps.monitoring.services.base_monitor.MonitoringEnvironmentContextService.build',
        return_value=None,
    )
    @mock.patch('src.apps.monitoring.models.MonitoringTask.objects.only')
    def test_empty_environment_keeps_context_unavailable(self, only_mock, _build_mock):
        only_mock.return_value.filter.return_value.first.return_value = SimpleNamespace(
            id=12,
            project_product_id=8,
            test_env=None,
        )

        monitor = MonitorBase(task_id=12)

        self.assertIsNone(monitor.test_config)
        self.assertIsNone(monitor.domain)
        self.assertEqual(monitor.database_configs, {})
