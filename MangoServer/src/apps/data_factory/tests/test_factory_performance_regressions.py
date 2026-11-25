from contextlib import contextmanager, nullcontext
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine, select, text
from sqlalchemy.pool import QueuePool

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy, DatasourceTypeBudget
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.execution.execution_metadata import DataFactoryExecutionMetadata as Metadata
from src.apps.data_factory.services.execution.runner import DataFactoryRunner
from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditHandle, SqlExecutionAuditService as Audit
from src.apps.data_factory.services.sql.sql_driver_audit import SqlDriverAuditService
from src.apps.data_factory.tests.test_datasource_performance import AtomicMemoryStore
from src.apps.test_center.enums.data_source import DataSourceTypeEnum


class ExecutionMetadataTests(SimpleTestCase):
    ddl = 'CREATE TABLE `example` (\n `id` bigint NOT NULL AUTO_INCREMENT,\n PRIMARY KEY (`id`)\n) ENGINE=InnoDB AUTO_INCREMENT=10'

    def setUp(self):
        self.target = SimpleNamespace(cache_key='binding-1-version-1', schema_name='example')
        self.entity = SimpleNamespace(table_name='example', primary_key='id')
        self.engine = Mock()
        self.engine.dialect.name = 'mysql'
        self.engine.connect.return_value = nullcontext(Mock())
        self.table = Table('example', MetaData(), Column('id', Integer, primary_key=True))

    def test_reuses_reflection_but_still_reads_fresh_ddl_before_every_insert(self):
        with patch('src.apps.data_factory.services.execution.execution_metadata.Table', return_value=self.table) as reflect, \
                patch('src.apps.data_factory.services.execution.execution_metadata.DataFactoryDiscover.get_mysql_table_definition',
                      return_value=self.ddl) as ddl, Metadata.scope():
            for _ in range(28):
                table, kinds = Metadata.resolve(self.entity, self.target, self.engine)
                self.assertIs(table, self.table)
                self.assertEqual(kinds, {'id': 'auto_increment'})
            self.assertEqual(reflect.call_count, 1)
            self.assertEqual(ddl.call_count, 29)

    def test_counter_changes_do_not_hide_real_structural_changes(self):
        with patch('src.apps.data_factory.services.execution.execution_metadata.Table', return_value=self.table), \
                patch('src.apps.data_factory.services.execution.execution_metadata.DataFactoryDiscover.get_mysql_table_definition',
                      side_effect=[self.ddl, self.ddl, self.ddl.replace('=10', '=11'),
                                   self.ddl.replace('bigint', 'varchar(32)')]), Metadata.scope():
            Metadata.resolve(self.entity, self.target, self.engine)
            Metadata.resolve(self.entity, self.target, self.engine)
            with self.assertRaises(DataFactoryError):
                Metadata.resolve(self.entity, self.target, self.engine)

    def test_quoted_literals_are_not_normalized(self):
        self.assertNotEqual(Metadata.definition_signature(self.ddl + " COMMENT='AUTO_INCREMENT=10'"),
                            Metadata.definition_signature(self.ddl + " COMMENT='AUTO_INCREMENT=11'"))

    def test_binding_versions_and_executions_do_not_share_tables(self):
        with patch('src.apps.data_factory.services.execution.execution_metadata.Table', return_value=self.table) as reflect, \
                patch('src.apps.data_factory.services.execution.execution_metadata.DataFactoryDiscover.get_mysql_table_definition',
                      return_value=self.ddl):
            with Metadata.scope():
                Metadata.resolve(self.entity, self.target, self.engine)
                Metadata.resolve(self.entity, SimpleNamespace(cache_key='binding-2', schema_name='example'), self.engine)
            with Metadata.scope():
                Metadata.resolve(self.entity, self.target, self.engine)
            self.assertEqual(reflect.call_count, 3)

    def test_schema_changes_during_initial_reflection_reject_insert(self):
        with patch('src.apps.data_factory.services.execution.execution_metadata.Table', return_value=self.table), \
                patch('src.apps.data_factory.services.execution.execution_metadata.DataFactoryDiscover.get_mysql_table_definition',
                      side_effect=[self.ddl, self.ddl.replace('bigint', 'varchar(32)')]), Metadata.scope():
            with self.assertRaises(DataFactoryError):
                Metadata.resolve(self.entity, self.target, self.engine)

    def test_supplied_connection_is_reused_for_both_ddl_reads_and_reflection(self):
        connection = Mock()
        with patch('src.apps.data_factory.services.execution.execution_metadata.Table', return_value=self.table) as reflect, \
                patch('src.apps.data_factory.services.execution.execution_metadata.DataFactoryDiscover.get_mysql_table_definition',
                      return_value=self.ddl) as ddl, Metadata.scope():
            Metadata.resolve(self.entity, self.target, self.engine, connection=connection)
            self.engine.connect.assert_not_called()
            self.assertIs(reflect.call_args.kwargs['autoload_with'], connection)
            self.assertEqual([call.args[0] for call in ddl.call_args_list], [connection, connection])


class LatePayloadTests(SimpleTestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', poolclass=QueuePool, pool_size=1, max_overflow=0, pool_timeout=0.1)
        self.addCleanup(self.engine.dispose)
        self.table = Table('example', MetaData(), Column('id', Integer, primary_key=True),
                           Column('name', String(32)), Column('requested', DateTime))
        self.table.metadata.create_all(self.engine)
        self.entity = SimpleNamespace(table_name='example', primary_key='id', unique_key='')
        self.target = SimpleNamespace(schema_name='', db_type=DataSourceTypeEnum.SQLITE.value)

    def test_only_tenant_is_generated_for_preflight_and_is_not_regenerated_for_insert(self):
        from src.apps.data_factory.enums import DataFactoryGeneratorTypeEnum as GeneratorType, DataFactoryOperationTypeEnum
        from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService as Resources
        from src.apps.data_factory.services.execution.generator import DataFactoryValueGenerator as Generator
        fields = [SimpleNamespace(name=name, generator_type=GeneratorType.FIXED.value, generator_config={},
            platform_type='string', nullable=False, primary_key=False, max_length=None, enum_values=[])
            for name in ('tenant_id', 'business_key', 'requested')]
        entity = SimpleNamespace(create_type=DataFactoryOperationTypeEnum.SQL.value,
            table_name='example', schema_name='', datafactoryfield_set=Mock())
        entity.datafactoryfield_set.all.return_value.order_by.return_value = fields
        template = SimpleNamespace(entity=entity, name='AUTO隔离资源', field_overrides={},
                                   cleanup_resources=[{}], project_product_id=1)
        generated, snapshots = [], []
        def generate(field, payload, context):
            generated.append(field.name)
            return {'tenant_id': '41', 'business_key': 'AUTO_ONE', 'requested': 'late'}[field.name]
        def insert(*args, **kwargs):
            kwargs['prepare_resources']()
            snapshots.append(list(generated))
            payload = kwargs['prepare_payload']()
            return {'created': payload}
        with patch('src.apps.data_factory.services.execution.parts.execution.DataFactoryDatasourceResolver.resolve_entity_binding'), \
                patch('src.apps.data_factory.services.execution.parts.execution.DataFactoryDatasourceResolver.require_binding_permission'), \
                patch('src.apps.data_factory.services.execution.parts.execution.DatasourceTargetService.resolve'), \
                patch.object(DataFactoryRunner, 'build_effective_fields', return_value=fields), \
                patch.object(DataFactoryRunner, 'resolve_dependencies') as dependencies, \
                patch.object(DataFactoryRunner, 'insert', side_effect=insert), \
                patch.object(Resources, 'normalize', return_value=[{'tenant_field': 'tenant_id'}]), \
                patch.object(Resources, 'preflight') as preflight, \
                patch.object(Generator, 'generate', side_effect=generate), \
                patch.object(Generator, 'replace_value', side_effect=lambda value, *_: value):
            result = DataFactoryRunner._create_by_template(template, Mock(), {}, {}, 0, None, set(), None, Mock())
        self.assertEqual(snapshots, [['tenant_id']])
        self.assertEqual(generated, ['tenant_id', 'business_key', 'requested'])
        self.assertEqual(result, {'tenant_id': '41', 'business_key': 'AUTO_ONE', 'requested': 'late'})
        self.assertEqual(preflight.call_args.args[1], {'tenant_id': '41'})
        dependencies.assert_called_once()

    def test_resource_preflight_holds_no_sql_connection_and_payload_is_generated_after_all_preparation(self):
        now = [datetime(2026, 1, 1, 12)]
        stages = []

        def preflight():
            self.assertEqual(self.engine.pool.checkedout(), 0)
            stages.append('preflight')
            now[0] += timedelta(minutes=2)

        def build():
            stages.append('payload')
            self.assertEqual(self.engine.pool.checkedout(), 1)
            return {'name': 'AUTO_LATE', 'requested': now[0] - timedelta(minutes=10)}

        prepare = Mock(side_effect=build)
        with patch('src.apps.data_factory.services.execution.parts.persistence.DataFactoryDatasource.get_worker_engine',
                   return_value=(self.engine, True)), nullcontext():
            result = DataFactoryRunner.insert(self.entity, self.target, {},
                prepare_resources=preflight, prepare_payload=prepare)
        self.assertEqual(stages, ['preflight', 'payload'])
        self.assertEqual(result['created']['requested'], datetime(2026, 1, 1, 11, 52))
        prepare.assert_called_once()
        self.assertEqual(self.engine.pool.checkedout(), 0)

    def test_resource_preflight_failure_does_not_generate_final_values_or_insert(self):
        prepare = Mock(return_value={'name': 'AUTO_MUST_NOT_CREATE'})
        preflight = Mock(side_effect=RuntimeError('AUTO_RESOURCE_UNAVAILABLE'))
        with patch('src.apps.data_factory.services.execution.parts.persistence.DataFactoryDatasource.get_worker_engine',
                   return_value=(self.engine, True)), self.assertRaises(DataFactoryError):
            DataFactoryRunner.insert(self.entity, self.target, {},
                prepare_resources=preflight, prepare_payload=prepare)
        preflight.assert_called_once()
        prepare.assert_not_called()
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(select(self.table)).all(), [])
        self.assertEqual(self.engine.pool.checkedout(), 0)

    def test_payload_or_preflight_failure_creates_no_business_row(self):
        with patch('src.apps.data_factory.services.execution.parts.persistence.DataFactoryDatasource.get_worker_engine',
                   return_value=(self.engine, True)), \
                nullcontext(), \
                self.assertRaises(DataFactoryError):
            DataFactoryRunner.insert(self.entity, self.target, {},
                prepare_payload=Mock(side_effect=RuntimeError('AUTO_PREFLIGHT_FAILURE')))
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(select(self.table)).all(), [])

    def test_one_connection_pool_inserts_and_returns_connection_without_nested_checkout(self):
        with patch('src.apps.data_factory.services.execution.parts.persistence.DataFactoryDatasource.get_worker_engine',
                   return_value=(self.engine, True)), \
                nullcontext():
            for number in range(3):
                DataFactoryRunner.insert(self.entity, self.target, {'name': f'AUTO_POOL_{number}'})
                self.assertEqual(self.engine.pool.checkedout(), 0)
        with self.engine.connect() as connection:
            self.assertEqual(len(connection.execute(select(self.table)).all()), 3)

    def test_invalid_primary_key_blocks_payload_generation_and_insert(self):
        prepare = Mock(return_value={'name': 'AUTO_UNSAFE'})
        self.entity.primary_key = 'not_the_primary_key'
        with patch('src.apps.data_factory.services.execution.parts.persistence.DataFactoryDatasource.get_worker_engine',
                   return_value=(self.engine, True)), \
                nullcontext(), \
                self.assertRaises(DataFactoryError):
            DataFactoryRunner.insert(self.entity, self.target, {}, prepare_payload=prepare)
        prepare.assert_not_called()
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(select(self.table)).all(), [])

    def test_stage_log_distinguishes_execution_from_ownership_persistence_and_logs_rollback(self):
        log_path = 'src.apps.data_factory.services.execution.parts.persistence.logger'
        with patch('src.apps.data_factory.services.execution.parts.persistence.DataFactoryDatasource.get_worker_engine',
                   return_value=(self.engine, True)), patch(log_path) as log:
            DataFactoryRunner.insert(self.entity, self.target, {},
                prepare_resources=lambda: None, prepare_payload=lambda: {'name': 'AUTO_SAFE'},
                before_commit=lambda result: 7)
            summary = next(call for call in log.debug.call_args_list
                           if call.args[0].startswith('event=factory_insert_finished'))
            self.assertTrue(summary.args[6])
            stages = summary.args[-1]
            self.assertEqual(set(stages), {'initial_metadata', 'resource_preflight', 'metadata_revalidation',
                'payload_generation', 'insert_statement', 'generated_values_readback',
                'ownership_and_item_persistence', 'other_including_audit_and_commit'})
            self.assertTrue(all(value >= 0 for value in stages.values()))
            log.reset_mock()
            with self.assertRaises(DataFactoryError):
                DataFactoryRunner.insert(self.entity, self.target, {'name': 'AUTO_ROLLBACK'},
                    before_commit=Mock(side_effect=RuntimeError('AUTO_ITEM_UNAVAILABLE')))
            summary = next(call for call in log.debug.call_args_list
                           if call.args[0].startswith('event=factory_insert_finished'))
            self.assertFalse(summary.args[6])
            self.assertIn('ownership_and_item_persistence', summary.args[-1])
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(select(self.table.c.name)).scalars().all(), ['AUTO_SAFE'])
        self.assertEqual(self.engine.pool.checkedout(), 0)

    def test_pre_admission_wait_is_recorded_without_inflating_sql_duration(self):
        handle = SqlExecutionAuditHandle(SimpleNamespace(source_detail={}), 0,
                                        wait_started=10)
        with patch('src.apps.data_factory.services.sql.sql_execution_audit.DatasourceWaitService.elapsed', return_value=10.2):
            duration = Audit.measured_duration(handle, 300)
        self.assertEqual(duration, 100)
        self.assertEqual(handle.record.source_detail['resource_wait_ms'], 200)
