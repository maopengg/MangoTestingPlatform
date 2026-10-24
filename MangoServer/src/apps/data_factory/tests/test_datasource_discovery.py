import json
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from src.apps.data_factory.models import Database
from src.apps.data_factory.services.datasource_discovery import DataSourceDiscoveryService
from src.apps.data_factory.services.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.discover import DataFactoryDiscover
from src.apps.test_center.exceptions import TestCenterError


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class DataSourceDiscoveryTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.database = Database(id=10, display_name='测试连接', db_type=0,
                                 host='mysql.example.com', port=3306, user='tester', password='private-secret',
                                 update_time=timezone.now())

    def test_missing_connection_is_business_error(self):
        with patch.object(Database.objects, 'filter') as query:
            query.return_value.first.return_value = None
            with self.assertRaises(TestCenterError):
                DataSourceDiscoveryService.get_database(99)

    def test_global_discovery_is_readonly_and_uses_maintenance_target(self):
        with patch.object(DataSourceDiscoveryService, 'get_database', return_value=self.database), \
                patch.object(DataSourceDiscoveryService, 'discover_database_names', return_value=['app']) as discover:
            self.assertEqual([{'name': 'app'}], DataSourceDiscoveryService.databases(10))
            self.assertEqual('', discover.call_args.args[0].database_name)
            self.assertFalse(hasattr(DataSourceDiscoveryService, 'import_databases'))

    def test_discovery_cache_isolated_by_credentials_and_refresh(self):
        with patch.object(DataSourceDiscoveryService, 'get_database', return_value=self.database), \
                patch.object(DataSourceDiscoveryService, 'discover_database_names', return_value=['app']) as discover:
            DataSourceDiscoveryService.databases(10)
            DataSourceDiscoveryService.databases(10)
            self.assertEqual(1, discover.call_count)
            self.database.password = 'changed'
            DataSourceDiscoveryService.databases(10)
            DataSourceDiscoveryService.databases(10, refresh=True)
            self.assertEqual(3, discover.call_count)

    def test_metadata_cache_isolated_by_library(self):
        first = DatasourceTargetService.build(self.database, database_name='first')
        second = DatasourceTargetService.build(self.database, database_name='second')
        with patch.object(DataFactoryDiscover, 'get_tables', return_value=[{'name': 'orders'}]) as discover, \
                patch('src.apps.data_factory.services.datasource_discovery.DataSourceConnectionService.timeout_seconds',
                      return_value=5):
            DataSourceDiscoveryService.tables(first)
            DataSourceDiscoveryService.tables(first)
            DataSourceDiscoveryService.tables(second)
            self.assertEqual(2, discover.call_count)
            DataSourceDiscoveryService.tables(second, refresh=True)
            self.assertEqual(3, discover.call_count)

    def test_postgres_discovery_checks_connect_permission(self):
        self.database.db_type = 1
        engine = MagicMock()
        engine.connect.return_value.__enter__.return_value.execute.return_value = [('app',)]
        with patch('src.apps.data_factory.services.datasource_discovery.DataFactoryDatasource.create_engine',
                   return_value=engine), \
                patch('src.apps.data_factory.services.datasource_discovery.DataSourceConnectionService.timeout_seconds',
                      return_value=5):
            self.assertEqual(['app'], DataSourceDiscoveryService.discover_database_names(
                DatasourceTargetService.maintenance(self.database)))
        sql = str(engine.connect.return_value.__enter__.return_value.execute.call_args.args[0])
        self.assertIn('has_database_privilege', sql)
        engine.dispose.assert_called_once()

    def test_redis_metadata_never_scans_keys(self):
        self.database.db_type = 10
        with self.assertRaises(TestCenterError):
            DataSourceDiscoveryService.tables(DatasourceTargetService.maintenance(self.database))

    def test_alias_ai_receives_bounded_metadata_without_credentials(self):
        engine = MagicMock()
        connection = engine.connect.return_value.__enter__.return_value
        connection.execute.return_value.mappings.return_value = [{'name': 'scores', 'comment': '评分记录'}]
        with patch.object(DataSourceDiscoveryService, 'get_database', return_value=self.database), \
                patch('src.apps.data_factory.services.datasource_discovery.DataFactoryDatasource.create_engine',
                      return_value=engine), \
                patch('src.apps.data_factory.services.datasource_discovery.DataSourceConnectionService.timeout_seconds',
                      return_value=5), \
                patch('src.apps.data_factory.services.datasource_discovery.AiService.json_chat') as ai:
            ai.return_value = {'choices': [{'message': {
                'content': json.dumps({'alias': '评测库', 'reason': '评分用途', 'confidence': 'medium'})}}]}
            result = DataSourceDiscoveryService.suggest_alias(10, 'evaluation')
            self.assertEqual('评测库', result['alias'])
            self.assertTrue(result['metadata_available'])
            content = ai.call_args.kwargs['messages'][1]['content']
            self.assertIn('评分记录', content)
            self.assertNotIn('private-secret', content)
            self.assertNotIn('mysql.example.com', content)
            self.assertIn('LIMIT 60', str(connection.execute.call_args.args[0]))
            engine.dispose.assert_called_once()

    def test_alias_without_library_does_not_read_tables(self):
        with patch.object(DataSourceDiscoveryService, 'get_database', return_value=self.database), \
                patch.object(DataSourceDiscoveryService, 'alias_metadata') as metadata, \
                patch('src.apps.data_factory.services.datasource_discovery.AiService.json_chat') as ai:
            ai.return_value = {
                'choices': [{'message': {'content': '{"alias":"测试库","reason":"参考连接","confidence":"low"}'}}]}
            self.assertFalse(DataSourceDiscoveryService.suggest_alias(10)['metadata_available'])
            metadata.assert_not_called()
