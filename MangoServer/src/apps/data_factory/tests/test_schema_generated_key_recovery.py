from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from sqlalchemy.dialects.mysql import dialect

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.services.schema.discover import DataFactoryDiscover
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasource
from src.apps.data_factory.services.schema.schema_monitor import DataFactorySchemaMonitorService


class GeneratedKeyRecoveryTests(SimpleTestCase):
    table_name = 'qa_testing.field_record_case'

    def discover(self, extra='', generated=True, ddl_error=None, empty_ddl=False, reader=None):
        database = SimpleNamespace(database_name='test_schema', id=22, password='')
        engine = MagicMock()
        connection = engine.connect.return_value.__enter__.return_value
        connection.dialect = dialect()
        metadata = MagicMock()
        metadata.mappings.return_value = [{
            'TABLE_NAME': self.table_name, 'COLUMN_NAME': 'mango_id', 'COLUMN_TYPE': 'bigint',
            'IS_NULLABLE': 'NO', 'COLUMN_KEY': 'PRI', 'EXTRA': extra,
            'COLUMN_DEFAULT': None, 'CHARACTER_MAXIMUM_LENGTH': None, 'ORDINAL_POSITION': 1,
        }]
        ddl = MagicMock()
        ddl.first.return_value = None if empty_ddl else (
            self.table_name,
            'CREATE TABLE `qa_testing.field_record_case` (\n'
            '  `mango_id` bigint NOT NULL' + (' /*T![auto_rand] AUTO_RANDOM(5) */' if generated else '') + ',\n'
            '  PRIMARY KEY (`mango_id`)\n)',
        )
        connection.execute.side_effect = [metadata, ddl_error if ddl_error else ddl]
        with patch.object(DataFactoryDatasource, 'create_engine', return_value=engine):
            try:
                schemas = (reader or DataFactoryDiscover.get_mysql_table_schemas)(database, [self.table_name])
            finally:
                engine.dispose.assert_called_once()
        return schemas[self.table_name], connection

    def test_repeated_discovery_preserves_auto_random_signature(self):
        expected = DataFactorySchemaMonitorService.columns_signature([
            {'name': 'mango_id', 'db_type': 'BIGINT', 'nullable': False,
             'primary_key': True, 'autoincrement': True, 'max_length': None},
        ])
        for _ in range(3):
            schema, connection = self.discover()
            actual = DataFactorySchemaMonitorService.columns_signature(schema['columns'])
            self.assertEqual(actual, expected)
            self.assertEqual(DataFactorySchemaMonitorService.describe_incompatible_differences(
                expected, actual, schema['columns'],
            ), [])
            ddl_sql = str(connection.execute.call_args_list[1].args[0])
            self.assertEqual(ddl_sql, 'SHOW CREATE TABLE test_schema.`qa_testing.field_record_case`')

    def test_actual_generation_removal_still_detected(self):
        before, _ = self.discover()
        after, _ = self.discover(generated=False)
        changes = DataFactorySchemaMonitorService.describe_incompatible_differences(
            DataFactorySchemaMonitorService.columns_signature(before['columns']),
            DataFactorySchemaMonitorService.columns_signature(after['columns']), after['columns'],
        )
        self.assertIn('autoincrement_removed', changes[0]['reasons'])

    def test_regular_auto_increment_does_not_read_ddl(self):
        schema, connection = self.discover(extra='auto_increment')
        self.assertTrue(schema['columns'][0]['autoincrement'])
        self.assertEqual(connection.execute.call_count, 1)

    def test_ddl_read_failure_does_not_return_incomplete_metadata(self):
        with self.assertRaises(DataFactoryError):
            self.discover(ddl_error=RuntimeError('DDL unavailable'))

    def test_empty_ddl_is_a_discovery_failure(self):
        with self.assertRaises(DataFactoryError):
            self.discover(empty_ddl=True)

    def scan(self, fail=False):
        from src.apps.data_factory.models import DataFactoryEntity, DataFactoryDatasourceBinding
        from src.apps.data_factory.services.datasource.datasource_target import DatasourceTargetService

        entity = SimpleNamespace(id=89, name='隔离记录', datasource_alias_id=22, table_name=self.table_name)
        database = SimpleNamespace(id=22, cache_key=(22, 'test_schema'), password='')
        binding = SimpleNamespace(id=3, datasource_alias_id=22, database_id=22, database=database)
        schema, _ = self.discover()
        expected = DataFactorySchemaMonitorService.columns_signature(schema['columns'])
        reader = DataFactoryDiscover.get_mysql_table_schemas
        def read_schemas(*_):
            result, _connection = self.discover(ddl_error=RuntimeError('DDL unavailable') if fail else None,
                                              reader=reader)
            return {self.table_name: result}
        with (
            patch.object(DataFactoryEntity.objects, 'select_related') as entities,
            patch.object(DataFactoryDatasourceBinding.objects, 'select_related') as bindings,
            patch.object(DatasourceTargetService, 'for_metadata', return_value=database),
            patch.object(DataFactorySchemaMonitorService, 'filter_validation_bindings', return_value=[binding]),
            patch.object(DataFactorySchemaMonitorService, 'entity_signatures', return_value={89: expected}),
            patch.object(DataFactoryDiscover, 'get_mysql_table_schemas', side_effect=read_schemas),
            patch.object(DataFactorySchemaMonitorService, 'disable_entity') as disable,
            patch.object(DataFactorySchemaMonitorService, '_reconcile_workbench_reviews') as reconcile,
        ):
            entities.return_value.filter.return_value = [entity]
            bindings.return_value.filter.return_value = [binding]
            result = DataFactorySchemaMonitorService.scan()
            disable.assert_not_called()
        return result, reconcile.call_args

    def test_three_complete_scans_do_not_disable_generated_primary_key(self):
        for _ in range(3):
            result, _ = self.scan()
            self.assertEqual(result['changed_entity_count'], 0)
            self.assertEqual(result['invalidated_template_count'], 0)
            self.assertEqual(result['failed_binding_count'], 0)
            self.assertEqual(result['errors'], [])

    def test_inconclusive_scan_does_not_disable_or_resolve_existing_risk(self):
        result, reconcile = self.scan(fail=True)
        self.assertEqual(result['changed_entity_count'], 0)
        self.assertEqual(result['failed_binding_count'], 1)
        self.assertEqual(reconcile.args[0], set())
