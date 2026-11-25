from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, text
from sqlalchemy.pool import QueuePool
from pymysql import OperationalError

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasource
from src.apps.data_factory.services.execution.execution_metadata import DataFactoryExecutionMetadata
from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
from src.apps.data_factory.services.execution.parts.persistence import DataFactoryRunnerPersistenceMixin as Persistence
from src.apps.data_factory.services.recovery.execution_recovery import DataFactoryExecutionRecovery as Recovery
from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService as Schedule
from src.apps.data_factory.services.cleanup.cleanup import DataFactoryCleanup


class FailureConvergenceTests(SimpleTestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', poolclass=QueuePool, pool_size=1, max_overflow=0, pool_timeout=0)
        self.addCleanup(self.engine.dispose)
        self.table = Table('fixture', MetaData(), Column('id', Integer, primary_key=True))
        self.table.create(self.engine)
        self.entity = SimpleNamespace(name='AUTO隔离示例', primary_key='id', table_name='fixture', unique_key='')
        self.database = SimpleNamespace(id=1, db_type=2)

    def insert(self, payload, prepare=None, prepare_resources=None):
        with patch.object(DataFactoryDatasource, 'get_worker_engine', return_value=(self.engine, True)), \
                patch.object(DataFactoryExecutionMetadata, 'resolve', return_value=(self.table, {})):
            return Persistence.insert(self.entity, self.database, payload, prepare_payload=prepare,
                                      prepare_resources=prepare_resources)

    def test_resource_preflight_releases_sql_connection_before_other_datasource_wait(self):
        def prepare():
            self.assertEqual(self.engine.pool.checkedout(), 0)
            with self.engine.connect() as connection:
                self.assertEqual(connection.execute(text('SELECT 1')).scalar(), 1)
        self.insert({'id': 1}, prepare_resources=prepare)
        self.assertEqual(self.engine.pool.checkedout(), 0)

    def test_unique_conflict_is_actionable_without_deleting_existing_rows(self):
        from sqlalchemy.exc import IntegrityError
        from pymysql import IntegrityError as MysqlIntegrityError
        self.insert({'id': 1})
        error = IntegrityError('INSERT INTO fixture VALUES (1)', {}, MysqlIntegrityError(1062, 'AUTO_PRIVATE'))
        with patch.object(self.engine.dialect, 'do_execute', side_effect=error):
            with self.assertRaises(DataFactoryError) as caught:
                self.insert({'id': 1})
        self.assertEqual(caught.exception.code, 34198)
        self.assertIn('固定唯一值', caught.exception.msg)
        self.assertNotIn('AUTO_PRIVATE', caught.exception.msg)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text('SELECT COUNT(*) FROM fixture')).scalar(), 1)
        self.assertEqual(self.engine.pool.checkedout(), 0)

    def test_server_query_timeout_is_not_platform_admission_timeout(self):
        with self.assertRaises(DataFactoryError) as caught:
            DataSourceErrorService.raise_sql_error(SimpleNamespace(db_type=0), OperationalError(3024, 'AUTO_PRIVATE'))
        self.assertEqual(caught.exception.code, 34199)
        self.assertIn('MAX_EXECUTION_TIME', caught.exception.msg)
        self.assertNotIn('AUTO_PRIVATE', caught.exception.msg)
        with DatasourceInfrastructureService.scope():
            DatasourceInfrastructureService.capture(caught.exception, result_unknown=True)
            self.assertFalse(DatasourceInfrastructureService.current())

    def test_running_report_is_never_cleaned_just_because_fixture_is_old(self):
        from src.apps.data_factory.constants import CLEANUP_REPORT_CONTEXT_KEY
        execution = SimpleNamespace(id=7, status=3, save=lambda **kwargs: self.fail('must not change active execution'),
            context={CLEANUP_REPORT_CONTEXT_KEY: {'parent_case_detail_id': 12, 'parent_attempt': 1}})
        with patch.object(Recovery, 'recover_inline_cleanup', return_value=0), \
                patch.object(Recovery, 'reconcile_manual_cleanup_states', return_value={'pending': 0, 'resolved': 0}), \
                patch.object(DataFactoryCleanup, 'reconcile_verified_cleanup', return_value=False), \
                patch('src.apps.data_factory.services.recovery.execution_recovery.DataFactoryExecution.objects') as objects, \
                patch.object(Schedule, 'validate_report_owner'), \
                patch.object(Recovery, 'report_execution_ended', return_value=False), \
                patch.object(Schedule, 'enqueue') as enqueue:
            objects.filter.return_value.exclude.return_value.filter.return_value.distinct.return_value.order_by.return_value.__getitem__.return_value = [execution]
            result = Recovery.recover()
        self.assertEqual(result['data_factory_recovery_deferred_count'], 1)
        self.assertEqual(execution.status, 3)
        enqueue.assert_not_called()

    def test_report_recovery_requires_terminal_trace_covering_this_factory_execution(self):
        from datetime import timedelta
        from django.utils import timezone
        from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
        from src.apps.test_center.enums import TestCaseTypeEnum
        from src.apps.auto_api.selectors.querysets import ApiQuerySelector
        now = timezone.now()
        detail = SimpleNamespace(id=12, status=1, type=TestCaseTypeEnum.API.value, summary_data={})
        trace = SimpleNamespace(started_at=now - timedelta(seconds=5), finished_at=None,
                                worker_name='AUTO_WORKER', summary={})
        owner = {'parent_case_detail_id': 12, 'parent_attempt': 1}
        execution = SimpleNamespace(create_time=now)
        with patch.object(TestCenterQuerySelector, 'test_suite_details') as details, \
                patch.object(ApiQuerySelector, 'api_case_execution_trace') as traces:
            details.return_value.filter.return_value.only.return_value.first.return_value = detail
            traces.return_value.filter.return_value.order_by.return_value.only.return_value.first.return_value = trace
            self.assertFalse(Recovery.report_execution_ended(owner, execution))
            trace.finished_at = now - timedelta(seconds=1)
            self.assertFalse(Recovery.report_execution_ended(owner, execution))
            trace.finished_at = now + timedelta(seconds=1)
            self.assertTrue(Recovery.report_execution_ended(owner, execution))
            detail.status = 3
            self.assertFalse(Recovery.report_execution_ended(owner, execution))

    def test_schema_drift_after_resource_preflight_blocks_insert(self):
        from src.apps.data_factory.exceptions import DATA_FACTORY_CONFIG_INVALID
        with patch.object(DataFactoryDatasource, 'get_worker_engine', return_value=(self.engine, True)), \
                patch.object(DataFactoryExecutionMetadata, 'resolve', side_effect=[
                    (self.table, {}), DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=('fixture：DDL changed',))]):
            with self.assertRaises(DataFactoryError):
                Persistence.insert(self.entity, self.database, {}, prepare_payload=lambda: {'id': 1})
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text('SELECT COUNT(*) FROM fixture')).scalar(), 0)
