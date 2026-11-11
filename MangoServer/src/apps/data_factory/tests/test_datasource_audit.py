import json
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import IntegrityError, OperationalError
from django.test import SimpleTestCase, override_settings
from sqlalchemy import create_engine, text

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.services.data_source_execution import DataSourceExecutionService
from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditHandle, SqlExecutionAuditService as Audit
from src.apps.data_factory.services.sql_driver_audit import SqlDriverAuditService
from src.apps.data_factory.selectors.execution_audit import ExecutionAuditSelector
from src.apps.system.api.serializers.sql_execution import SqlExecutionRecordSerializer
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.common.enums.system_error import SystemErrorEventSource


def record(**values):
    return SimpleNamespace(id=1, status='running', request_id='request', source_detail={},
                           source_stage='create', slow_threshold_ms=20000, save=Mock(), **values)


class DatasourceAuditTests(SimpleTestCase):
    def setUp(self):
        governor = patch('src.apps.data_factory.services.datasource_governor.DatasourceGovernorService.operation',
                         side_effect=lambda target, **kwargs: nullcontext())
        governor.start()
        self.addCleanup(governor.stop)

    def test_queue_time_is_recorded_separately_and_does_not_create_slow_sql(self):
        from src.apps.data_factory.services.datasource_wait import _wait_elapsed
        token = _wait_elapsed.set(0)
        try:
            target = record()
            handle = SqlExecutionAuditHandle(target, 0)
            _wait_elapsed.set(60)
            with patch.object(Audit, 'notify_slow'):
                Audit.finish_success(handle, {'row_count': 1}, 61000)
            self.assertEqual(target.duration_ms, 1000)
            self.assertEqual(target.source_detail['resource_wait_ms'], 60000)
            self.assertFalse(target.is_slow)
        finally:
            _wait_elapsed.reset(token)

    def test_streaming_query_unknown_rowcount_is_not_persisted_as_affected_rows(self):
        result = Mock(returns_rows=True, rowcount=2 ** 64 - 1)
        result.keys.return_value = ['id']
        result.fetchmany.return_value = [SimpleNamespace(_mapping={'id': 7})]
        connection = Mock()
        connection.execution_options.return_value = connection
        connection.execute.return_value = result
        engine = Mock()
        engine.connect.return_value = nullcontext(connection)
        with patch('src.apps.data_factory.services.data_source_execution.DataFactoryDatasource.create_engine',
                   return_value=engine), patch.object(DataSourceExecutionService, 'max_rows', return_value=10):
            value = DataSourceExecutionService.execute_sql(Mock(), 'SELECT id FROM example', is_write=False)
        target = record()
        with patch.object(Audit, 'notify_slow'):
            Audit.finish_success(SqlExecutionAuditHandle(target, 0), value, 1)
        self.assertEqual(value['rows'], [{'id': 7}])
        self.assertEqual(target.row_count, 1)
        self.assertEqual(target.affected_rows, 0)
        self.assertEqual(target.status, 'success')
        target.save.assert_called_once()
        engine.dispose.assert_called_once()

    def test_write_affected_rows_are_preserved(self):
        result = Mock(returns_rows=False, rowcount=3)
        connection = Mock()
        connection.execute.return_value = result
        engine = Mock()
        engine.begin.return_value = nullcontext(connection)
        with patch('src.apps.data_factory.services.data_source_execution.DataFactoryDatasource.create_engine',
                   return_value=engine):
            value = DataSourceExecutionService.execute_sql(
                Mock(), 'DELETE FROM example WHERE id = 7', is_write=True)
        self.assertEqual(value['affected_rows'], 3)
        self.assertEqual(value['row_count'], 0)

    def test_result_redacts_positional_sensitive_columns_and_nested_es_documents(self):
        preview, truncated = Audit.result_preview({
            'columns': ['id', 'password', 'access_token'], 'rows': [[1, 'hidden-pass', 'hidden-token']],
            'result': [[1, 'hidden-pass', 'hidden-token']],
            'hits': {'hits': [{'_source': {'authorization': 'hidden-header', 'name': 'AUTO示例'}}]},
        })
        self.assertFalse(truncated)
        for value in ('hidden-pass', 'hidden-token', 'hidden-header'):
            self.assertNotIn(value, preview)
        self.assertIn('AUTO示例', preview)

    def test_result_keeps_redis_value_and_limits_unicode_characters(self):
        preview, truncated = Audit.result_preview({'type': 'redis', 'result': '中文' * 1000})
        self.assertTrue(truncated)
        self.assertEqual(len(preview), 1000)
        self.assertIn('中文', preview)

    def test_execution_content_is_type_specific_and_redacted(self):
        self.assertEqual(Audit.safe_content('SET token:key "hidden"', 10), 'SET ? ?')
        self.assertNotIn('hidden', Audit.safe_content("SELECT * FROM t WHERE password='hidden'", 0))
        self.assertNotIn('hidden', Audit.safe_content({'query': {'term': {'password': 'hidden'}}}, 20))

    def test_scope_is_restored_after_failure(self):
        with self.assertRaises(RuntimeError):
            with Audit.scope('first'):
                self.assertEqual(Audit.active(), 'first')
                with Audit.scope('nested'):
                    self.assertEqual(Audit.active(), 'nested')
                self.assertEqual(Audit.active(), 'first')
                raise RuntimeError()
        self.assertIsNone(Audit.active())

    @patch.object(Audit, 'finish_success')
    @patch.object(Audit, 'start')
    def test_nested_protocol_call_does_not_duplicate_record(self, start, finish):
        target_record = record()
        target_record.database_id = 7
        target_record.datasource_type = 0
        start.return_value = SqlExecutionAuditHandle(target_record, 0)
        result = Audit.call(SimpleNamespace(id=7, db_type=0), 'outer', lambda: Audit.call(
            SimpleNamespace(id=7, db_type=0), 'inner', lambda: {'result': 3}))
        self.assertEqual(result['result'], 3)
        start.assert_called_once()
        finish.assert_called_once()

    @patch.object(Audit, 'finish_failure')
    @patch.object(Audit, 'start')
    def test_start_failure_blocks_callback(self, start, failed):
        start.side_effect = DataFactoryError.__new__(DataFactoryError)
        callback = Mock()
        with self.assertRaises(DataFactoryError):
            Audit.call(SimpleNamespace(id=7), 'operation', callback)
        callback.assert_not_called()
        failed.assert_not_called()

    @patch.object(Audit, 'notify_slow')
    def test_row_limit_audit_keeps_exact_reason_without_false_unknown_read(self, notify):
        from src.apps.data_factory.services.datasource_cost import DatasourceCostService
        from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService as Infrastructure
        for is_write in (False, True):
            with self.assertRaises(DataFactoryError) as caught:
                DatasourceCostService.abort_result(Mock(), Mock(), limit=100, observed_rows=101, is_write=is_write)
            target = record()
            with Infrastructure.scope():
                Audit.finish_failure(SqlExecutionAuditHandle(target, 0), caught.exception, 1)
                self.assertEqual(bool(Infrastructure.current()), is_write)
            self.assertIn('[34194]', target.error_message)
            self.assertIn('100 行', target.error_message)
            self.assertIn('至少 101 行', target.error_message)
            self.assertEqual(target.source_detail['outcome_unknown'], is_write)
            self.assertEqual(target.status, 'fail')

    @patch.object(Audit, 'notify_slow')
    def test_wrapped_timeout_and_error_text_are_safe(self, notify):
        error = RuntimeError('hidden-password')
        error.__cause__ = TimeoutError()
        target = record()
        Audit.finish_failure(SqlExecutionAuditHandle(target, 0), error, 21000)
        self.assertEqual(target.status, 'timeout')
        self.assertTrue(target.is_slow)
        self.assertTrue(target.source_detail['outcome_unknown'])
        self.assertNotIn('hidden-password', target.error_message)
        target.save.assert_called_once()

    @patch.object(Audit, 'notify_slow')
    def test_rejected_admission_is_not_unknown_but_prior_statement_stays_unknown(self, notify):
        from src.apps.data_factory.exceptions import DATASOURCE_ADMISSION_TIMEOUT
        error = DataFactoryError(DATASOURCE_ADMISSION_TIMEOUT)
        error._datasource_not_sent = True
        for sent in (False, True):
            target = record()
            Audit.finish_failure(SqlExecutionAuditHandle(target, 0, statement_claimed=sent), error, 1)
            self.assertEqual(target.source_detail['outcome_unknown'], sent)
            self.assertEqual(target.status, 'fail')

    @patch.object(Audit, 'notify_slow')
    def test_fixed_admission_reason_is_preserved_without_leaking_exception_context(self, notify):
        from src.apps.data_factory.exceptions import DATASOURCE_RECONCILIATION_REQUIRED
        error = DataFactoryError(DATASOURCE_RECONCILIATION_REQUIRED)
        error._datasource_not_sent = True
        error.__cause__ = RuntimeError('test-only-secret')
        target = record()
        Audit.finish_failure(SqlExecutionAuditHandle(target, 0), error, 1)
        self.assertIn('[34191]', target.error_message)
        self.assertIn('结果未确认的历史占用', target.error_message)
        self.assertNotIn('test-only-secret', target.error_message)
        self.assertFalse(target.source_detail['outcome_unknown'])

    @patch.object(Audit, 'notify_slow')
    def test_settlement_failure_does_not_claim_operation_was_never_sent(self, notify):
        from src.apps.data_factory.exceptions import DATASOURCE_SETTLEMENT_FAILED, DATASOURCE_GOVERNOR_UNAVAILABLE
        for definition in (DATASOURCE_SETTLEMENT_FAILED, DATASOURCE_GOVERNOR_UNAVAILABLE):
            target = record()
            Audit.finish_failure(SqlExecutionAuditHandle(target, 0, statement_claimed=True),
                                 DataFactoryError(definition), 1)
            self.assertTrue(target.source_detail['outcome_unknown'])
            self.assertNotIn('未发送', target.error_message)
            self.assertNotIn('未获准', target.error_message)
        self.assertIn('配额结算', DataFactoryError(DATASOURCE_SETTLEMENT_FAILED).msg)

    @patch.object(Audit, 'save_completion')
    def test_rollback_audit_does_not_claim_success_when_commit_response_unknown(self, save):
        from src.apps.data_factory.services.factory_sql_execution import DataFactorySqlExecutionService as FactoryAudit
        from src.apps.data_factory.exceptions import DATASOURCE_SETTLEMENT_FAILED
        for error, unknown in ((RuntimeError('snapshot-failed'), False), (TimeoutError('commit-response'), True),
                               (DataFactoryError(DATASOURCE_SETTLEMENT_FAILED), True)):
            target = record()
            FactoryAudit.mark_rolled_back([SqlExecutionAuditHandle(target, 0)], error)
            self.assertEqual(target.status, 'fail' if unknown else 'rolled_back')
            self.assertEqual(target.source_detail['outcome_unknown'], unknown)

    def test_success_summary_cannot_be_replayed_as_full_response(self):
        target = record()
        target.status = 'success'
        for truncated in (False, True):
            target.result_truncated = truncated
            with self.assertRaises(DataFactoryError) as error:
                Audit.replay_result(SqlExecutionAuditHandle(target, 0, existing=True))
            self.assertEqual(error.exception.code, 34176)

    @patch('src.apps.data_factory.services.sql_execution_audit.report_system_error')
    def test_completion_failure_is_explicit(self, report):
        target = record()
        target.save.side_effect = OSError()
        with self.assertRaises(DataFactoryError) as error, self.assertLogs(Audit.__module__, level='ERROR'):
            Audit.save_completion(target, update_fields=['status'])
        self.assertEqual(error.exception.code, 34174)
        self.assertIs(report.call_args.args[0], target.save.side_effect)
        self.assertEqual(report.call_args.kwargs['request_path'], 'datasource_audit:completion')

    @override_settings(MANGO_SERVICE_NAME='mcp-service')
    @patch('src.apps.data_factory.services.sql_execution_audit.report_system_error')
    @patch.object(Audit, 'database_alias', return_value='default')
    @patch('src.apps.data_factory.services.sql_execution_audit.transaction.atomic', side_effect=lambda **_: nullcontext())
    @patch('src.apps.data_factory.services.sql_execution_audit.SystemConfigService.get_sql_slow_query_threshold_seconds', return_value=20)
    @patch('src.apps.data_factory.services.sql_execution_audit.SqlExecutionRecord.objects')
    def test_audit_creation_failure_records_original_error_and_blocks_execution(self, objects, threshold, atomic, alias, report):
        original = OperationalError(1054, "Unknown column 'datasource_type'")
        objects.using.return_value.create.side_effect = original
        target = SimpleNamespace(id=7, db_type=20, database_name='sample')
        callback = Mock()
        with self.assertRaises(DataFactoryError) as caught, self.assertLogs(Audit.__module__, level='ERROR'):
            Audit.call(target, {'index': 'example', 'query': {}}, callback)
        self.assertEqual(caught.exception.code, 34173)
        self.assertIs(caught.exception.__cause__, original)
        self.assertNotIn('datasource_type', caught.exception.msg)
        callback.assert_not_called()
        report.assert_called_once_with(original, source=SystemErrorEventSource.MCP,
                                       service_name='mcp-service', request_path='datasource_audit:create')

    @patch('src.apps.data_factory.services.sql_execution_audit.report_system_error', side_effect=RuntimeError('reporter offline'))
    def test_reporting_failure_keeps_original_completion_error_and_never_retries(self, report):
        target = record()
        original = OperationalError('audit offline')
        target.save.side_effect = original
        with self.assertRaises(DataFactoryError) as caught, self.assertLogs(Audit.__module__, level='ERROR'):
            Audit.save_completion(target, update_fields=['status'])
        self.assertEqual(caught.exception.code, 34174)
        self.assertIs(caught.exception.__cause__, original)
        target.save.assert_called_once()
        report.assert_called_once()

    @patch('src.apps.data_factory.services.sql_execution_audit.report_system_error')
    def test_audit_failure_source_follows_running_service(self, report):
        for service, source in (('core-api', SystemErrorEventSource.HTTP),
                                ('api-worker', SystemErrorEventSource.API_WORKER),
                                ('scheduler-service', SystemErrorEventSource.SCHEDULER)):
            with self.subTest(service=service), override_settings(MANGO_SERVICE_NAME=service):
                Audit.report_audit_failure(OperationalError('schema mismatch'), 'create')
                self.assertEqual(report.call_args.kwargs['source'], source)
                self.assertEqual(report.call_args.kwargs['service_name'], service)

    @override_settings(MANGO_SERVICE_NAME='mcp-service')
    @patch('src.apps.system.services.runtime_center.system_error_event.SystemErrorEventService.record')
    def test_original_audit_failure_reaches_system_error_recorder(self, save_event):
        try:
            raise OperationalError(1054, "Unknown column 'datasource_type'")
        except OperationalError as error:
            Audit.report_audit_failure(error, 'create')
        save_event.assert_called_once()
        event = save_event.call_args.kwargs
        self.assertEqual(event['exception_type'], 'OperationalError')
        self.assertEqual(event['source'], SystemErrorEventSource.MCP)
        self.assertEqual(event['request_path'], 'datasource_audit:create')
        self.assertIn('datasource_type', event['message'])
        self.assertIn('OperationalError', event['trace'])

    @patch('src.apps.task_center.services.workbench.todo.WorkbenchTodoService.record_slow_sql')
    def test_todo_failure_does_not_replace_result(self, slow):
        slow.side_effect = OSError()
        with self.assertLogs(Audit.__module__, level='ERROR'):
            Audit.notify_slow(SimpleNamespace(id=3, is_slow=True))

    @patch.object(Audit, 'notify_slow')
    def test_sensitive_redis_result_is_hidden(self, _):
        target = record()
        target.source_detail['sensitive_result'] = True
        Audit.finish_success(SqlExecutionAuditHandle(target, 0), {'result': 'hidden-token'}, 2)
        self.assertNotIn('hidden-token', target.result_preview)

    @patch.object(Audit, 'database_alias', return_value='default')
    @patch('src.apps.data_factory.services.sql_execution_audit.transaction.atomic', return_value=nullcontext())
    @patch('src.apps.data_factory.services.sql_execution_audit.SystemConfigService.get_sql_slow_query_threshold_seconds', return_value=20)
    @patch('src.apps.data_factory.services.sql_execution_audit.SqlExecutionRecord.objects')
    def test_new_record_has_type_snapshot_and_environment_zero(self, objects, *_):
        target = SimpleNamespace(id=7, db_type=0, database_name='sample', redis_db=None)
        binding = SimpleNamespace(database=target, database_id=7, datasource_alias_id=8)
        Audit.start(binding=binding, project_product_id=3, test_env=0, sql='SELECT 1', parameters={},
                    source_context={'source_type': 'api_case', 'source_stage': 'front', 'case_id': 9},
                    request_id='same-request', started_monotonic=0)
        values = objects.using.return_value.create.call_args.kwargs
        self.assertEqual(values['datasource_type'], 0)
        self.assertEqual(values['test_env'], 0)
        self.assertEqual(values['source_id'], 9)
        self.assertEqual(values['datasource_alias_id'], 8)
        self.assertEqual(values['database_id'], 7)
        self.assertEqual(values['source_detail']['target_kind'], 'logical_database')

    @patch.object(Audit, 'database_alias', return_value='default')
    @patch('src.apps.data_factory.services.sql_execution_audit.transaction.atomic', side_effect=lambda **_: nullcontext())
    @patch('src.apps.data_factory.services.sql_execution_audit.SystemConfigService.get_sql_slow_query_threshold_seconds', return_value=20)
    @patch('src.apps.data_factory.services.sql_execution_audit.SqlExecutionRecord.objects')
    def test_duplicate_id_is_claimed_atomically_and_conflicting_operation_rejected(self, objects, *_):
        target = SimpleNamespace(id=7, db_type=10, database_name='', redis_db=0)
        kwargs = dict(database=target, sql='GET key', parameters={}, source_context={
            'source_type': 'mcp', 'source_stage': 'query', 'operator_id': 4},
                      request_id='same-request', started_monotonic=0)
        Audit.start(**kwargs)
        values = objects.using.return_value.create.call_args.kwargs
        objects.using.return_value.create.side_effect = IntegrityError()
        existing = SimpleNamespace(source_detail=values['source_detail'])
        objects.using.return_value.get.return_value = existing
        self.assertTrue(Audit.start(**kwargs).existing)
        with self.assertRaises(DataFactoryError) as error:
            Audit.start(**{**kwargs, 'sql': 'GET other-key'})
        self.assertEqual(error.exception.code, 34175)

    @patch.object(Audit, 'notify_slow')
    @patch.object(Audit, 'start')
    def test_sqlalchemy_real_cursor_records_results_and_no_nested_duplicates(self, start, _):
        handles = []

        def new_handle(**kwargs):
            handle = SqlExecutionAuditHandle(record(), kwargs['started_monotonic'])
            handles.append(handle)
            return handle

        start.side_effect = new_handle
        engine = create_engine('sqlite:///:memory:')
        SqlDriverAuditService.attach(engine, SimpleNamespace(id=7, db_type=DataSourceTypeEnum.SQLITE.value))
        try:
            with engine.connect() as connection:
                rows = connection.execute(text("SELECT 1 AS id, 'hidden-password' AS password")).fetchall()
                self.assertEqual(rows[0][0], 1)
                statement_record = handles[-1].record
                self.assertEqual(statement_record.row_count, 1)
                self.assertNotIn('hidden-password', statement_record.result_preview)
                before = len(handles)
                with Audit.scope(handles[-1]):
                    connection.execute(text('SELECT 2')).fetchall()
                    connection.execute(text('SELECT 3')).fetchall()
                self.assertEqual(len(handles), before + 1)
                self.assertEqual(start.call_args.kwargs['source_context']['source_stage'], 'generated_key_lookup')
                with self.assertRaises(Exception):
                    connection.execute(text('SELECT * FROM absent_table'))
                self.assertEqual(handles[-1].record.status, 'fail')
        finally:
            engine.dispose()

    @patch('src.apps.data_factory.services.sql_execution_audit.SqlExecutionRecord.objects')
    @patch.object(Audit, 'reconcile_slow', return_value=0)
    def test_stale_recovery_only_marks_unknown_and_never_executes(self, reconcile, objects):
        from django.utils import timezone
        target = record()
        from datetime import timedelta
        target.update_time = timezone.now() - timedelta(days=2)
        objects.filter.return_value.order_by.return_value = [target]
        objects.filter.return_value.update.return_value = 1
        with patch.object(DataSourceExecutionService, 'execute_backend') as backend:
            self.assertEqual(Audit.recover_stale(), {'recovered_audit_count': 1, 'reconciled_slow_audit_count': 0})
        backend.assert_not_called()
        values = objects.filter.return_value.update.call_args.kwargs
        self.assertEqual(values['status'], 'fail')
        self.assertTrue(values['source_detail']['outcome_unknown'])

    @patch('src.apps.data_factory.services.sql_execution_audit.SqlExecutionRecord.objects')
    @patch.object(Audit, 'reconcile_slow', return_value=0)
    def test_recent_running_audit_requires_exact_completed_owner_evidence(self, reconcile, objects):
        from datetime import timedelta
        from django.utils import timezone
        from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
        target = record()
        target.update_time = target.create_time = timezone.now()-timedelta(minutes=2)
        target.source_detail = {'execution_owner': {'process_token': 'AUTO_OWNER'}}
        objects.filter.return_value.order_by.return_value = [target]
        objects.filter.return_value.update.return_value = 1
        with patch.object(ServiceHeartbeatService, 'completed_mcp_process', return_value=False):
            self.assertEqual(Audit.recover_stale()['recovered_audit_count'], 0)
            objects.filter.return_value.update.assert_not_called()
        with patch.object(ServiceHeartbeatService, 'completed_mcp_process', return_value=True):
            self.assertEqual(Audit.recover_stale()['recovered_audit_count'], 1)
        changes = objects.filter.return_value.update.call_args.kwargs
        self.assertTrue(changes['source_detail']['outcome_unknown'])
        self.assertTrue(changes['source_detail']['execution_owner_completed'])
        self.assertEqual(changes['status'], 'fail')

    @patch('src.apps.data_factory.services.data_source_execution.DatasourceTargetService.resolve')
    @patch('src.apps.data_factory.services.data_source_execution.DataFactoryDatasourceResolver')
    @patch.object(DataSourceExecutionService, 'execute_backend')
    @patch.object(Audit, 'start')
    @patch.object(Audit, 'finish_success')
    @patch.object(Audit, 'finish_failure')
    def test_unified_entry_audits_all_three_backends_and_failures(self, failed, finish, start, backend, resolver, target):
        for db_type, operation in ((0, 'SELECT 1'), (10, 'GET sample'), (20, {'index': 'example', 'query': {}})):
            binding = SimpleNamespace(database=SimpleNamespace(db_type=db_type), datasource_alias_id=8)
            resolver.resolve_binding_by_env.return_value = binding
            start.return_value = SqlExecutionAuditHandle(record(is_slow=False, duration_ms=1), 0)
            backend.side_effect = None
            backend.return_value = {'result': 1}
            result = DataSourceExecutionService.execute(datasource_alias_id=8, project_product_id=3,
                                                         test_env=0, operation_config=operation)
            self.assertEqual(result['sql_execution_id'], 1)
            self.assertEqual(result['datasource_type'], db_type)
            backend.side_effect = TimeoutError()
            with self.assertRaises(Exception):
                DataSourceExecutionService.execute(datasource_alias_id=8, project_product_id=3,
                                                   test_env=0, operation_config=operation)
        self.assertEqual(finish.call_count, 3)
        self.assertEqual(failed.call_count, 3)


class AuditVisibilityTests(SimpleTestCase):
    @patch('src.apps.data_factory.selectors.execution_audit.SqlExecutionRecord.objects')
    @patch('src.apps.data_factory.selectors.execution_audit.ProjectProductScopeService')
    @patch('src.apps.data_factory.selectors.execution_audit.PermissionMenuService')
    def test_missing_identity_and_menu_are_denied_even_for_admin(self, permissions, scope, objects):
        queryset = objects.select_related.return_value
        ExecutionAuditSelector.visible(None)
        queryset.none.assert_called_once()
        permissions.permission_keys_for_user.return_value = set()
        ExecutionAuditSelector.visible(Mock())
        self.assertEqual(queryset.none.call_count, 2)
        permissions.is_effective_super_admin.assert_not_called()

    @patch('src.apps.data_factory.selectors.execution_audit.SqlExecutionRecord.objects')
    @patch('src.apps.data_factory.selectors.execution_audit.ProjectProductScopeService')
    @patch('src.apps.data_factory.selectors.execution_audit.PermissionMenuService')
    def test_connection_scope_requires_its_menu_not_only_product_scope(self, permissions, scope, objects):
        permissions.is_effective_super_admin.return_value = False
        scope.can_view_all_project_data.return_value = False
        scope.project_product_ids_for_user.return_value = [3]
        queryset = objects.select_related.return_value
        permissions.permission_keys_for_user.return_value = {'system.sql_execution:read'}
        ExecutionAuditSelector.visible(Mock())
        product_predicate = queryset.filter.call_args.args[0]
        self.assertEqual(product_predicate.connector, 'AND')
        permissions.permission_keys_for_user.return_value.add('config.datasource:read')
        ExecutionAuditSelector.visible(Mock())
        self.assertEqual(queryset.filter.call_args.args[0].connector, 'OR')

    def test_serializer_historical_type_and_empty_scope(self):
        historical = SimpleNamespace(datasource_type=None, database=SimpleNamespace(db_type=10),
                                     test_env=None, source_detail={})
        self.assertEqual(SqlExecutionRecordSerializer.get_datasource_type_name(historical), 'Redis（当前配置）')
        self.assertEqual(SqlExecutionRecordSerializer.get_test_env_name(historical), '不适用')
        self.assertEqual(SqlExecutionRecordSerializer.get_database_name(historical), '-')
