from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone
from sqlalchemy.exc import OperationalError

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.models import Database, DataFactoryDatasourceBinding, DataFactoryEntity
from src.apps.data_factory.services.data_source_error import DataSourceErrorService
from src.apps.data_factory.services.datasource import DataFactoryDatasource
from src.apps.data_factory.services.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.execution_snapshot import build_insert_snapshot


class DatasourceTargetTests(SimpleTestCase):
    def setUp(self):
        self.connection = Database(id=7, display_name='共享连接', host='db.example.com', port=3306,
                                   db_type=0, user='tester', password='secret', update_time=timezone.now())

    def binding(self, name='', schema='', redis_db=None):
        return SimpleNamespace(id=8, database=self.connection, database_id=7,
                               database_name=name, schema_name=schema, redis_db=redis_db, environment=1)

    def test_connection_no_longer_stores_target_and_binding_does(self):
        fields = {field.name for field in Database._meta.fields}
        self.assertNotIn('name', fields)
        self.assertNotIn('test_object', fields)
        self.assertIn('file_path', fields)
        fields = {field.name for field in DataFactoryDatasourceBinding._meta.fields}
        self.assertTrue({'database_name', 'schema_name', 'redis_db'} <= fields)
        self.assertNotIn('test_object', fields)
        self.assertIn('schema_name', {field.name for field in DataFactoryEntity._meta.fields})

    def test_mysql_empty_default_is_allowed(self):
        target = DatasourceTargetService.resolve(self.binding())
        self.assertEqual('', target.database_name)
        self.assertIn('/?charset=', DataFactoryDatasource.build_url(target))
        self.assertNotIn('secret', repr(target))
        self.assertNotIn('password', target.model_dump())
        with self.assertRaises(DataFactoryError):
            DatasourceTargetService.for_metadata(self.binding())

    def test_libraries_and_versions_isolate_cache_without_mutating_connection(self):
        first = DatasourceTargetService.resolve(self.binding('first'))
        second = DatasourceTargetService.resolve(self.binding('second'))
        self.assertNotEqual(first.cache_key, second.cache_key)
        self.connection.update_time += timedelta(seconds=1)
        changed = DatasourceTargetService.resolve(self.binding('first'))
        self.assertNotEqual(first.cache_key, changed.cache_key)
        self.assertFalse(hasattr(self.connection, 'database_name'))

    def test_postgres_database_and_schema_are_independent(self):
        self.connection.db_type = 1
        default = DatasourceTargetService.resolve(self.binding())
        self.assertEqual('postgres', default.database_name)
        target = DatasourceTargetService.resolve(self.binding('app', 'billing'), schema_name='orders')
        self.assertEqual(('app', 'orders'), (target.database_name, target.schema_name))

    def test_redis_db_required_and_part_of_cache(self):
        self.connection.db_type = 10
        with self.assertRaises(DataFactoryError):
            DatasourceTargetService.resolve(self.binding())
        first = DatasourceTargetService.resolve(self.binding(redis_db=0))
        second = DatasourceTargetService.resolve(self.binding(redis_db=1))
        self.assertNotEqual(first.cache_key, second.cache_key)
        for invalid in [-1, True, '0']:
            with self.assertRaises(DataFactoryError):
                DatasourceTargetService.resolve(self.binding(redis_db=invalid))

    def test_nonrelational_rejects_library_and_schema(self):
        self.connection.db_type = 20
        for binding in [self.binding('app'), self.binding(schema='public')]:
            with self.assertRaises(DataFactoryError):
                DatasourceTargetService.resolve(binding)

    def test_sqlite_never_creates_missing_file(self):
        self.connection.db_type = 2
        self.connection.file_path = '/missing/database.sqlite'
        with patch('src.apps.data_factory.services.datasource_target.Path.is_file', return_value=False):
            with self.assertRaises(DataFactoryError):
                DatasourceTargetService.maintenance(self.connection)

    def test_snapshot_keeps_original_target_and_rejects_changed_connection(self):
        entity = SimpleNamespace(id=9, datasource_alias_id=6, schema_name='', table_name='orders', primary_key='id')
        snapshot = build_insert_snapshot(entity, self.binding('first'))
        resolved = DatasourceTargetService.from_snapshot(self.connection, snapshot)
        self.assertEqual('first', resolved.database_name)
        self.connection.update_time += timedelta(seconds=1)
        with self.assertRaises(DataFactoryError):
            DatasourceTargetService.from_snapshot(self.connection, snapshot)
        with self.assertRaises(DataFactoryError):
            DatasourceTargetService.from_snapshot(self.connection, {})

    def test_no_default_database_error_has_actionable_message(self):
        error = OperationalError('SELECT * FROM orders', {}, RuntimeError('No database selected'))
        with self.assertRaises(DataFactoryError) as raised:
            DataSourceErrorService.raise_sql_error(DatasourceTargetService.resolve(self.binding()), error)
        self.assertEqual(34172, raised.exception.code)
        self.assertIn('库.表', raised.exception.msg)

    def test_worker_pools_isolate_libraries_and_dispose_changed_connection(self):
        from src.processes.api_worker.db_context import WorkerDbContext
        from unittest.mock import MagicMock
        context = WorkerDbContext()
        first_engine, second_engine, new_engine = MagicMock(), MagicMock(), MagicMock()
        first = DatasourceTargetService.resolve(self.binding('first'))
        second = DatasourceTargetService.resolve(self.binding('second'))
        with patch.object(DataFactoryDatasource, 'create_engine',
                          side_effect=[first_engine, second_engine, new_engine]) as factory:
            self.assertIs(first_engine, context.get_data_factory_engine(first))
            self.assertIs(first_engine, context.get_data_factory_engine(first))
            self.assertIs(second_engine, context.get_data_factory_engine(second))
            self.assertEqual(2, factory.call_count)
            self.connection.update_time += timedelta(seconds=1)
            self.assertIs(new_engine,
                          context.get_data_factory_engine(DatasourceTargetService.resolve(self.binding('first'))))
            first_engine.dispose.assert_called_once()
            second_engine.dispose.assert_called_once()
            context.close_all()
            new_engine.dispose.assert_called_once()
