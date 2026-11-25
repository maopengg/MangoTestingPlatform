from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.db import connections
from django.db.backends.sqlite3.base import DatabaseWrapper
from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.auto_api.models import ApiCaseExecutionTrace, ApiCaseExecutionStep
from src.apps.auto_api.selectors.case_list_execution import ApiCaseListExecutionSelector as Selector
from src.apps.auto_api.services.execution_trace.report_reconciliation import ApiReportTraceReconciliationService as Reconcile
from src.apps.test_center.models import TestSuite, TestSuiteDetails, ExecutionResult
from src.apps.test_center.enums.reporting import ReportRecoveryCauseEnum, ReportRecoveryActionEnum
from src.apps.test_center.schemas.infrastructure import ReportRecoveryControl


class ReportExecutionStateTests(SimpleTestCase):
    """状态投影及补偿使用独立内存 ORM，不迁移、不连接业务库。"""

    def setUp(self):
        self.original = connections['default']
        self.memory = DatabaseWrapper({'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:',
            'TIME_ZONE': None, 'CONN_HEALTH_CHECKS': False, 'CONN_MAX_AGE': 0, 'OPTIONS': {},
            'AUTOCOMMIT': True}, alias='report-state-only-memory')
        connections['report-state-only-memory'] = self.memory
        self.addCleanup(self.restore_connection)
        with self.memory.schema_editor() as editor:
            for model in (TestSuite, TestSuiteDetails, ExecutionResult, ApiCaseExecutionTrace, ApiCaseExecutionStep):
                editor.create_model(model)
        self.memory.disable_constraint_checking()
        connections['default'] = self.memory
        self.now = timezone.now()
        self.suite = TestSuite.objects.create(id=2, project_product_id=1, user_id=1, test_env=0, status=3, is_notice=0)
        self.detail = TestSuiteDetails.objects.create(id=7, test_suite=self.suite, type=1,
            project_product_id=1, test_env=0, case_id=11, status=3, retry=1, case_sum=4,
            push_time=self.now - timedelta(seconds=1), summary_data={'children': [], 'meta': {
                'dispatch_started_at': (self.now - timedelta(seconds=1)).isoformat()}})
        self.trace = ApiCaseExecutionTrace.objects.create(trace_id='example-trace', source_type=1,
            case_id=11, test_env=0, test_suite_id=2, test_suite_detail_id=7, status=3,
            started_at=self.now, summary={'report_attempt': 1})
        ApiCaseExecutionTrace.objects.filter(id=self.trace.id).update(update_time=self.now - timedelta(minutes=3))
        self.step = ApiCaseExecutionStep.objects.create(trace=self.trace, step_key='cleanup',
            step_type='data_factory_cleanup', step_name='清理场景数据工厂', status=3, started_at=self.now)

    def restore_connection(self):
        connections['default'] = self.original
        del connections['report-state-only-memory']
        self.memory.close()

    def row(self, **kwargs):
        return Selector.with_trace_status(ApiCaseExecutionTrace.objects.filter(id=self.trace.id), **kwargs).get()

    def recovery(self, owner_ended=False):
        control = ReportRecoveryControl(attempt=1, cause=ReportRecoveryCauseEnum.EXECUTION_TIMEOUT,
            action=ReportRecoveryActionEnum.RECOVER, observed_at=self.now, next_check_at=self.now,
            deadline_at=self.now + timedelta(minutes=10), owner_ended=owner_ended)
        self.detail.summary_data['meta']['execution_control'] = control.model_dump(mode='json')
        self.detail.save(update_fields=['summary_data'])

    def test_legacy_block_is_failed_not_stale_running_and_steps_are_closed(self):
        self.detail.status = 6
        self.detail.save(update_fields=['status'])
        self.assertEqual(self.row().display_status, 0)
        self.assertEqual(Reconcile.reconcile(), 1)
        self.trace.refresh_from_db(); self.step.refresh_from_db(); self.detail.refresh_from_db()
        self.assertEqual((self.trace.status, self.step.status, self.detail.status, self.detail.retry), (0, 0, 6, 1))
        self.assertIsNotNone(self.step.finished_at)
        self.assertEqual(Reconcile.reconcile(), 0)

    def test_active_recovery_is_a_phase_not_a_new_terminal_status(self):
        self.recovery()
        row = self.row()
        self.assertEqual((row.display_status, row.report_phase), (3, 'automatic_recovery'))
        self.assertEqual(Reconcile.reconcile(), 0)
        self.trace.refresh_from_db()
        self.assertEqual(self.trace.status, 3)

    def test_old_interrupted_trace_duration_exceeds_int32_without_truncation(self):
        self.detail.status = 6
        self.detail.summary_data['meta']['dispatch_started_at'] = (self.now - timedelta(days=61)).isoformat()
        self.detail.save(update_fields=['status', 'summary_data'])
        started = self.now - timedelta(days=60)
        ApiCaseExecutionTrace.objects.filter(id=self.trace.id).update(started_at=started)
        ApiCaseExecutionStep.objects.filter(id=self.step.id).update(started_at=started)
        with patch('src.apps.auto_api.services.execution_trace.recorder.timezone.now', return_value=self.now):
            self.assertEqual(Reconcile.reconcile(), 1)
        for row in (self.trace, self.step):
            row.refresh_from_db()
            self.assertEqual(row._meta.get_field('duration_ms').get_internal_type(), 'BigIntegerField')
            self.assertEqual(row.duration_ms, 60 * 24 * 60 * 60 * 1000)
            self.assertGreater(row.duration_ms, 2**31 - 1)
            self.assertEqual(row.status, 0)
        self.assertEqual(Reconcile.reconcile(), 0)

    def test_reconciliation_logs_safe_code_and_stack_then_continues(self):
        from django.db import DataError
        with patch('src.apps.auto_api.services.execution_trace.report_reconciliation.ApiReportTraceStateSelector.candidates',
                   return_value=[7, 8]), \
                patch('src.apps.auto_api.services.execution_trace.report_reconciliation.TestSuiteInfrastructureService.reconcile_trace',
                      side_effect=[DataError(1264, 'example-sensitive-sql'), True]), \
                self.assertLogs('system', level='ERROR') as logs:
            self.assertEqual(Reconcile.reconcile(), 1)
        output = '\n'.join(logs.output)
        self.assertIn('detail=7', output)
        self.assertIn('database_code=1264', output)
        self.assertIn('traceback=', output)
        self.assertNotIn('example-sensitive-sql', output)

    def test_confirmed_owner_end_closes_steps_even_when_trace_already_failed(self):
        self.recovery(owner_ended=True)
        ApiCaseExecutionTrace.objects.filter(id=self.trace.id).update(status=0, finished_at=self.now)
        self.assertEqual(Reconcile.reconcile(), 1)
        self.step.refresh_from_db(); self.detail.refresh_from_db()
        self.assertEqual((self.step.status, self.detail.status), (0, 3))
        self.assertEqual(self.row().report_phase, 'automatic_recovery')

    def test_new_attempt_and_wrong_environment_do_not_relabel_old_trace(self):
        ApiCaseExecutionTrace.objects.filter(id=self.trace.id).update(status=0, finished_at=self.now)
        TestSuiteDetails.objects.filter(id=7).update(retry=2, status=3)
        self.assertEqual(self.row().display_status, 0)
        self.assertIsNone(self.row().report_phase)
        self.assertEqual(Reconcile.reconcile(), 0)
        TestSuiteDetails.objects.filter(id=7).update(retry=1, test_env=1, status=1)
        self.assertEqual(self.row().display_status, 0)

    def test_queued_retry_updates_list_but_does_not_rewrite_historical_trace(self):
        ApiCaseExecutionTrace.objects.filter(id=self.trace.id).update(status=0, finished_at=self.now)
        TestSuiteDetails.objects.filter(id=7).update(status=2)
        self.assertEqual(self.row(include_queued=True).display_status, 2)
        self.assertEqual(self.row().display_status, 0)

    def test_parent_stop_and_final_failure_override_stale_trace_status(self):
        TestSuiteDetails.objects.filter(id=7).update(status=0)
        self.assertEqual(self.row().display_status, 0)
        TestSuite.objects.filter(id=2).update(status=5)
        self.assertEqual(self.row().display_status, 5)

    def test_list_payload_preserves_recovery_phase(self):
        row = SimpleNamespace(list_trace_id='example-trace', list_status=3, list_phase='automatic_recovery',
            list_version='published', list_revision_id=1, list_has_history=True, list_started_at=self.now,
            list_result_env=0)
        self.assertEqual(Selector.presentation(row, 0)['phase'], 'automatic_recovery')

    def test_legacy_phase_and_terminal_steps_do_not_become_pending_again(self):
        self.detail.summary_data['meta']['execution_control'] = {'phase': 'infrastructure_blocked', 'attempt': 1}
        self.detail.save(update_fields=['summary_data'])
        self.assertEqual(self.row().display_status, 0)
        passed = ApiCaseExecutionStep.objects.create(trace=self.trace, step_key='request',
            step_type='request', step_name='接口请求', status=1, started_at=self.now, finished_at=self.now)
        self.assertEqual(Reconcile.reconcile(), 1)
        passed.refresh_from_db()
        self.assertEqual(passed.status, 1)

    def test_completed_result_sync_never_clears_resource_or_retry_evidence(self):
        TestSuiteDetails.objects.filter(id=7).update(status=1)
        original = self.detail.summary_data
        self.assertEqual(self.row().display_status, 1)
        self.assertEqual(Reconcile.reconcile(), 1)
        self.detail.refresh_from_db()
        self.assertEqual((self.detail.status, self.detail.retry, self.detail.summary_data), (1, 1, original))

    def test_mysql_phase_projection_is_unquoted_without_connecting_to_mysql(self):
        from django.db.backends.mysql.base import DatabaseWrapper as MySQLWrapper
        mysql = MySQLWrapper({'ENGINE': 'django.db.backends.mysql', 'NAME': 'unused',
            'OPTIONS': {}, 'TIME_ZONE': None, 'CONN_HEALTH_CHECKS': False, 'CONN_MAX_AGE': 0,
            'AUTOCOMMIT': True}, alias='report-state-mysql-compile-only')
        mysql.mysql_server_data = {'version': '8.0.36', 'sql_mode': '', 'default_storage_engine': 'InnoDB',
                                   'sql_auto_is_null': False, 'lower_case_table_names': False, 'has_zoneinfo_database': True}
        query = Selector.with_trace_status(ApiCaseExecutionTrace.objects.all()).values('report_phase').query
        sql, parameters = query.get_compiler(connection=mysql).as_sql()
        self.assertTrue('JSON_UNQUOTE(JSON_EXTRACT(' in sql or ' ->> ' in sql)
        self.assertTrue(any('execution_control' in str(value) and 'phase' in str(value) for value in parameters))
