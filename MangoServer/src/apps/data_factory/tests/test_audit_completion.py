from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from copy import deepcopy
from tempfile import TemporaryDirectory
from threading import Lock
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import IntegrityError, OperationalError
from django.test import SimpleTestCase
from sqlalchemy import create_engine, text

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.models import SqlExecutionRecord
from src.apps.data_factory.services.sql.audit_request import DatasourceAuditRequestService as Requests
from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService as Audit
from src.apps.data_factory.services.sql.sql_driver_audit import AuditedResultCursor, SqlDriverAuditService
from src.apps.test_center.enums.data_source import DataSourceTypeEnum


class AuditCompletionTests(SimpleTestCase):
    def setUp(self):
        self.saved = []
        self.lock = Lock()
        self.target = SimpleNamespace(id=7, db_type=DataSourceTypeEnum.SQLITE.value, database_name='example')
        for target, value in ((Audit, 'notify_slow'), (Audit, 'database_alias')):
            mock = patch.object(target, value, return_value='default' if value == 'database_alias' else None)
            mock.start()
            self.addCleanup(mock.stop)
        atomic = patch('src.apps.data_factory.services.sql.sql_execution_audit.transaction.atomic',
                       side_effect=lambda **_: nullcontext())
        atomic.start()
        self.addCleanup(atomic.stop)
        threshold = patch('src.apps.data_factory.services.sql.sql_execution_audit.SystemConfigService.get_sql_slow_query_threshold_seconds',
                          return_value=20)
        threshold.start()
        self.addCleanup(threshold.stop)
        saver = patch.object(SqlExecutionRecord, 'save', autospec=True, side_effect=self.persist)
        self.save = saver.start()
        self.addCleanup(saver.stop)

    def persist(self, record, **kwargs):
        with self.lock:
            if kwargs.get('force_insert'):
                record.id = len(self.saved) + 1
                record._state.adding = False
                self.saved.append(deepcopy(vars(record)))

    def start(self):
        return Audit.start(database=self.target, sql='SELECT 1', parameters={}, request_id=None,
            source_context={'source_type': 'api_case', 'source_stage': 'query', 'case_id': 17}, started_monotonic=0)

    def test_prepare_does_not_write_and_repeated_completion_inserts_once(self):
        handle = self.start()
        self.assertIsNone(handle.record.id)
        self.save.assert_not_called()
        Audit.finish_success(handle, {'rows': [{'value': '样' * 1200}], 'row_count': 1}, 12)
        Audit.finish_success(handle, {}, 13)
        Audit.finish_failure(handle, RuntimeError(), 14)
        self.assertEqual(len(self.saved), 1)
        row = self.saved[0]
        self.assertEqual(row['status'], 'success')
        self.assertEqual(row['duration_ms'], 12)
        self.assertEqual(len(row['result_preview']), 1000)
        self.assertTrue(row['result_truncated'])
        self.assertIn('started_at', row['source_detail'])
        self.assertIn('finished_at', row['source_detail'])

    def test_streaming_partial_reads_write_only_on_close(self):
        handle = self.start()
        raw = Mock(description=[('id',)], rowcount=-1)
        raw.fetchmany.side_effect = [[(1,)], [(2,)]]
        cursor = AuditedResultCursor(raw, handle)
        self.assertEqual(cursor.fetchmany(1), [(1,)])
        self.assertEqual(cursor.fetchmany(1), [(2,)])
        self.save.assert_not_called()
        cursor.close()
        cursor.close()
        self.assertEqual(len(self.saved), 1)
        self.assertEqual(self.saved[0]['row_count'], 2)
        self.assertFalse(self.saved[0]['source_detail']['result_fully_read'])

    def test_streaming_read_error_is_saved_once_without_replaying_fetch(self):
        handle = self.start()
        raw = Mock(description=[('id',)])
        raw.fetchone.side_effect = TimeoutError('private response')
        cursor = AuditedResultCursor(raw, handle)
        with self.assertRaises(TimeoutError):
            cursor.fetchone()
        cursor.close()
        self.assertEqual(len(self.saved), 1)
        self.assertEqual(self.saved[0]['status'], 'timeout')
        self.assertNotIn('private response', self.saved[0]['error_message'])
        raw.fetchone.assert_called_once()

    def test_insert_retry_never_replays_business_callback(self):
        calls = []
        def save(record, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                raise OperationalError(2013, 'audit connection lost')
            self.persist(record, **kwargs)
        self.save.side_effect = save
        callback = Mock(return_value={'row_count': 1})
        with patch('src.apps.data_factory.services.sql.sql_execution_audit.connections') as connections:
            connections.__getitem__.return_value.in_atomic_block = False
            Audit.call(self.target, 'SELECT 1', callback)
        callback.assert_called_once()
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(self.saved), 1)

    def test_insert_commit_response_lost_reuses_unique_request_record(self):
        handle = self.start()
        self.save.side_effect = IntegrityError(1062, 'request already stored')
        stored = SimpleNamespace(pk=45, source_detail=handle.record.source_detail)
        with patch('src.apps.data_factory.services.sql.sql_execution_audit.SqlExecutionRecord.objects') as manager:
            manager.using.return_value.get.return_value = stored
            Audit.finish_success(handle, {'row_count': 1}, 1)
        self.assertEqual(handle.record.pk, 45)
        self.assertFalse(handle.record._state.adding)
        self.save.assert_called_once()

    def test_real_sql_cursor_commit_rollback_and_errors_have_terminal_records(self):
        engine = create_engine('sqlite:///:memory:')
        SqlDriverAuditService.attach(engine, self.target)
        try:
            with Audit.source({'case_id': 17}), engine.connect() as connection:
                result = connection.execute(text('SELECT 1 AS id'))
                before = len(self.saved)
                self.assertEqual(result.fetchmany(1)[0][0], 1)
                self.assertEqual(len(self.saved), before)
                result.close()
                result.close()
                connection.commit()
                with self.assertRaises(Exception):
                    connection.execute(text('SELECT id FROM missing_example'))
                connection.rollback()
                connection.execute(text('SELECT 2'))  # 未消费结果也在连接归还时收尾。
        finally:
            engine.dispose()
        statements = [row for row in self.saved if row['source_detail']['operation'] == 'select']
        self.assertEqual(len(statements), 3)
        self.assertEqual([row['status'] for row in statements], ['success', 'fail', 'success'])
        self.assertTrue(any(row['sql_text'] == 'COMMIT' and row['status'] == 'success' for row in self.saved))
        self.assertTrue(any(row['sql_text'] == 'ROLLBACK' for row in self.saved))
        self.assertTrue(all(row['status'] != 'running' for row in self.saved))

    def test_parallel_cases_keep_sources_and_finish_once_without_business_throttle(self):
        with TemporaryDirectory() as directory:
            engine = create_engine('sqlite:///' + directory + '/example.db', pool_size=10)
            SqlDriverAuditService.attach(engine, self.target)
            def run(case_id):
                with Audit.source({'case_id': case_id, 'test_suite_id': 99}), engine.connect() as connection:
                    result = connection.execute(text('SELECT :value AS id'), {'value': case_id}).fetchall()
                    return result[0][0]
            try:
                with ThreadPoolExecutor(max_workers=10) as executor:
                    self.assertEqual(list(executor.map(run, range(1, 101))), list(range(1, 101)))
            finally:
                engine.dispose()
        selects = [row for row in self.saved if row['source_detail']['operation'] == 'select']
        self.assertEqual(len(selects), 100)
        self.assertEqual({row['source_detail']['case_id'] for row in selects}, set(range(1, 101)))
        self.assertEqual(len({row['request_id'] for row in self.saved}), len(self.saved))

    def test_commit_response_timeout_is_not_a_successful_commit(self):
        import sqlite3
        class LostCommitResponse(sqlite3.Connection):
            def commit(self):
                super().commit()
                raise TimeoutError('response lost after commit')
        engine = create_engine('sqlite://', creator=lambda: sqlite3.connect(':memory:', factory=LostCommitResponse))
        SqlDriverAuditService.attach(engine, self.target)
        try:
            with engine.connect() as connection:
                connection.exec_driver_sql('CREATE TABLE example(id INTEGER PRIMARY KEY)')
                connection.exec_driver_sql('INSERT INTO example(id) VALUES (1)')
                with self.assertRaises(TimeoutError):
                    connection.commit()
        finally:
            engine.dispose()
        commits = [row for row in self.saved if row['sql_text'] == 'COMMIT']
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0]['status'], 'timeout')
        self.assertTrue(commits[0]['source_detail']['outcome_unknown'])
        insert = next(row for row in self.saved if row['source_detail']['operation'] == 'insert')
        self.assertEqual(insert['status'], 'success')

    def test_dedup_survives_worker_change_and_unknown_request_is_not_replayed(self):
        data, lock = {}, Lock()
        store = Mock()
        store.control_connection.side_effect = lambda: nullcontext()
        def claim(key, value, **kwargs):
            self.assertIsNone(kwargs['ttl'])
            with lock:
                if key in data:
                    return False
                data[key] = value
                return True
        store.set_if_absent.side_effect = claim
        store.get.side_effect = data.get
        with patch.object(Requests, 'store', return_value=store):
            Requests.claim('example-request', 'a' * 64)
            with self.assertRaises(DataFactoryError) as error:
                Requests.claim('example-request', 'a' * 64)
            self.assertEqual(error.exception.code, 34164)
            with self.assertRaises(DataFactoryError) as error:
                Requests.claim('example-request', 'b' * 64)
            self.assertEqual(error.exception.code, 34175)

    def test_driver_failure_reason_is_specific_but_does_not_leak_values(self):
        from pymysql.err import IntegrityError as MysqlIntegrityError
        handle = self.start()
        Audit.finish_failure(handle, MysqlIntegrityError(1062, "Duplicate entry 'private-token'"), 1)
        self.assertIn('唯一键冲突', self.saved[0]['error_message'])
        self.assertNotIn('private-token', self.saved[0]['error_message'])
        self.assertFalse(self.saved[0]['source_detail']['outcome_unknown'])

    def test_later_cleanup_rejection_does_not_change_successful_query(self):
        from src.apps.data_factory.exceptions import DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID
        Audit.call(self.target, 'SELECT 1', lambda: {'row_count': 1})
        with self.assertRaises(DataFactoryError):
            raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID)
        self.assertEqual(len(self.saved), 1)
        self.assertEqual(self.saved[0]['status'], 'success')

    def test_outer_transaction_failure_does_not_mark_successful_select_failed(self):
        from src.apps.data_factory.services.sql.factory_sql_execution import DataFactorySqlExecutionService as Factory
        handle = self.start()
        Audit.finish_success(handle, {'row_count': 1}, 1)
        Factory.mark_rolled_back([handle], TimeoutError('commit response lost'))
        self.assertEqual(handle.record.status, 'success')
        self.assertEqual(handle.record.source_detail['transaction_outcome'], 'unknown')
        self.assertFalse(handle.record.source_detail.get('outcome_unknown', False))

    def test_audit_failure_never_hides_original_driver_error_or_reexecutes(self):
        from pymysql.err import IntegrityError as MysqlIntegrityError
        original = MysqlIntegrityError(1062, 'private duplicate value')
        callback = Mock(side_effect=original)
        self.save.side_effect = OperationalError(2013, 'audit offline')
        with patch.object(Audit, 'report_audit_failure') as report, \
                patch('src.apps.data_factory.services.sql.sql_execution_audit.connections') as connections, \
                self.assertLogs(Audit.__module__, level='ERROR'):
            connections.__getitem__.return_value.in_atomic_block = False
            with self.assertRaises(MysqlIntegrityError) as error:
                Audit.call(self.target, 'INSERT INTO example VALUES (1)', callback)
        self.assertIs(error.exception, original)
        self.assertEqual(original._datasource_audit_failure_code, 34174)
        self.assertEqual(self.save.call_count, 3)
        callback.assert_called_once()
        report.assert_called_once()

    def test_summary_failure_preserves_physical_success(self):
        summary = Mock(side_effect=TypeError('formatter'))
        with self.assertRaises(TypeError):
            Audit.call(self.target, 'SELECT 1', lambda: {'row_count': 1}, result_summary=summary)
        self.assertEqual(len(self.saved), 1)
        self.assertEqual(self.saved[0]['status'], 'success')

    def test_case_origin_is_frozen_for_scheduler_and_cannot_be_forged(self):
        from src.apps.data_factory.constants import EXECUTION_AUDIT_CONTEXT_KEY
        from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService as Schedule
        from src.apps.data_factory.services.sql.factory_sql_execution import DataFactorySqlExecutionService as Factory
        from src.apps.auto_api.services.execution_trace.recorder import ApiCaseExecutionTraceRecorder
        recorder = ApiCaseExecutionTraceRecorder.__new__(ApiCaseExecutionTraceRecorder)
        recorder.trace = SimpleNamespace(case_id=17, test_suite_id=99, test_suite_detail_id=31, trace_id='example-trace',
                                        worker_name='example-worker', id=5)
        with recorder.execution_scope():
            saved = Schedule.execution_context({EXECUTION_AUDIT_CONTEXT_KEY: {'case_id': 999}})
        self.assertNotIn('case_id', Audit.current_source())
        execution = SimpleNamespace(id=7, source_type=5, source_id=88, execution_no='DFEXAMPLE', context=saved)
        source = Factory.build_source_context(execution=execution, stage='cleanup')
        self.assertEqual(source['case_id'], 17)
        self.assertEqual(source['test_suite_id'], 99)
        self.assertEqual(source['test_suite_detail_id'], 31)
        self.assertEqual(source['trace_id'], 'example-trace')
