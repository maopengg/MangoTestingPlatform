from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from django.db import connections, transaction, OperationalError
from django.utils import timezone

from src.apps.auto_api.models import ApiCaseExecutionTrace, ApiCaseExecutionStep
from src.apps.auto_api.models.resource_cleanup import ApiCaseExecutionResource
from src.apps.auto_api.models.callback import ApiCaseCallbackRun
from src.apps.auto_api.models.mock import ApiMockRequestLog
from src.apps.auto_api.services.execution_trace.retention import ApiTraceRetentionService as Retention


class TraceRetentionBatchTests(TestCase):
    """临时 SQLite ORM 回归，不运行迁移、不连接 test/dev 环境。"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.directory = TemporaryDirectory(prefix='mango-trace-retention-')
        cls.alias = 'isolated_trace_retention'
        config = deepcopy(connections['default'].settings_dict)
        config.update(ENGINE='django.db.backends.sqlite3', NAME=str(Path(cls.directory.name) / 'trace.db'),
                      USER='', PASSWORD='', HOST='', PORT='', OPTIONS={}, TIME_ZONE=None)
        connections.databases[cls.alias] = config
        cls.connection = connections[cls.alias]
        cls.connection.disable_constraint_checking()
        with cls.connection.schema_editor() as editor:
            for model in (ApiCaseExecutionTrace, ApiCaseExecutionStep, ApiCaseExecutionResource, ApiCaseCallbackRun,
                          ApiMockRequestLog):
                # SQLite 不支持 MySQL 的大小写敏感排序规则。
                for field in model._meta.local_fields:
                    if getattr(field, 'db_collation', None):
                        cls.connection.connection.create_collation(field.db_collation, lambda a, b: (a > b) - (a < b))
                editor.create_model(model)
        cls.connection.disable_constraint_checking()

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()
        del connections.databases[cls.alias]
        delattr(connections._connections, cls.alias)
        cls.directory.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.traces = ApiCaseExecutionTrace.objects.db_manager(self.alias)
        self.steps = ApiCaseExecutionStep.objects.db_manager(self.alias)
        self.resources = ApiCaseExecutionResource.objects.db_manager(self.alias)
        self.callbacks = ApiCaseCallbackRun.objects.db_manager(self.alias)
        self.deliveries = ApiMockRequestLog.objects.db_manager(self.alias)
        for rows in (self.deliveries, self.callbacks, self.resources, self.steps, self.traces):
            rows.all()._raw_delete(self.alias)
        atomic = transaction.atomic
        self.guards = [patch.object(ApiCaseExecutionTrace, 'objects', self.traces),
                       patch.object(ApiCaseExecutionStep, 'objects', self.steps),
                       patch.object(ApiCaseExecutionResource, 'objects', self.resources),
                       patch.object(ApiCaseCallbackRun, 'objects', self.callbacks),
                       patch.object(ApiMockRequestLog, 'objects', self.deliveries),
                       patch('src.apps.auto_api.services.execution_trace.retention.transaction.atomic',
                             side_effect=lambda *a, **kw: atomic(using=self.alias))]
        for guard in self.guards:
            guard.start()
            self.addCleanup(guard.stop)
        self.cutoff = timezone.now() - timedelta(days=30)

    def trace(self, name, **kwargs):
        trace = self.traces.create(trace_id=name, source_type=3, case_id=1, status=1,
                                   finished_at=timezone.now(), **kwargs)
        self.traces.filter(id=trace.id).update(create_time=self.cutoff - timedelta(days=1))
        return trace

    def test_children_are_bounded_and_restart_continues_without_parent_cascade(self):
        trace = self.trace('AUTO_BATCH')
        self.steps.bulk_create([ApiCaseExecutionStep(trace_id=trace.id, step_key=str(i), step_type='request',
            step_name='AUTO', status=1) for i in range(5)])
        with patch.object(Retention, 'CHILD_BATCH_SIZE', 2), patch.object(Retention, 'MAX_BATCHES', 1):
            result = Retention.cleanup(self.cutoff)
            self.assertEqual(result['deleted_count'], 2)
            self.assertTrue(result['has_more'])
            self.assertTrue(self.traces.filter(id=trace.id).exists())
            self.assertEqual(self.steps.count(), 3)
        self.assertEqual(Retention.cleanup(self.cutoff)['deleted_count'], 4)
        self.assertFalse(self.traces.exists())

    def test_active_review_and_resource_evidence_are_retained(self):
        active = self.trace('AUTO_ACTIVE')
        self.traces.filter(id=active.id).update(status=3, finished_at=None)
        self.trace('AUTO_REVIEW', summary={'review_required': True})
        owned = self.trace('AUTO_OWNED')
        self.resources.create(case_id=1, trace_id=owned.id, step_id=1, parameter_id=1,
            test_env=0, rule_key='AUTO_RULE', rule={}, proof={}, status='failed')
        self.trace('AUTO_TERMINAL')
        self.assertEqual(Retention.cleanup(self.cutoff)['deleted_count'], 1)
        self.assertEqual(self.traces.count(), 3)

    def test_recent_trace_is_never_deleted(self):
        self.traces.create(trace_id='AUTO_RECENT', source_type=3, case_id=1, status=1, finished_at=timezone.now())
        self.assertEqual(Retention.cleanup(self.cutoff)['deleted_count'], 0)

    def test_callback_evidence_is_not_cascade_deleted(self):
        trace = self.trace('AUTO_CALLBACK')
        self.callbacks.create(execution_key='AUTO_EXECUTION', rule_key='AUTO_RULE', case_id=1,
            mock_config_id=1, test_env=0, trace_id=trace.id, dependency_digest='AUTO_DIGEST',
            correlation_value='AUTO_VALUE', correlation_key='AUTO_KEY', deadline=timezone.now())
        self.assertEqual(Retention.cleanup(self.cutoff)['deleted_count'], 0)
        self.assertTrue(self.traces.filter(id=trace.id).exists())
        self.assertEqual(self.callbacks.count(), 1)

    def test_lock_or_disconnect_rolls_back_only_current_batch_and_can_resume(self):
        trace = self.trace('AUTO_RETRY')
        self.steps.create(trace_id=trace.id, step_key='1', step_type='request', step_name='AUTO', status=1)
        for code in (1205, 2013):
            with self.subTest(code=code), patch('django.db.models.query.QuerySet.delete',
                    side_effect=OperationalError(code, 'AUTO_INTERRUPTED')):
                with self.assertRaises(OperationalError):
                    Retention.cleanup(self.cutoff)
            self.assertEqual(self.steps.count(), 1)
        self.assertEqual(Retention.cleanup(self.cutoff)['deleted_count'], 2)

    def test_expired_completed_ledgers_callbacks_and_deliveries_are_deleted_in_bounded_batches(self):
        trace = self.trace('AUTO_COMPLETED_EVIDENCE')
        resource = self.resources.create(case_id=1, trace=trace, step_id=1, parameter_id=1,
            test_env=0, rule_key='rule', rule={}, proof={}, status='cleaned')
        self.resources.filter(id=resource.id).update(update_time=self.cutoff - timedelta(days=1))
        run = self.callbacks.create(execution_key='exec', rule_key='callback', case_id=1, mock_config_id=1,
            test_env=0, trace=trace, dependency_digest='digest', correlation_value='value', correlation_key='key',
            deadline=self.cutoff, status='passed', finished_at=self.cutoff - timedelta(days=1))
        self.deliveries.bulk_create([ApiMockRequestLog(mock_config_id=1, callback_run=run,
            trace_id=f'log{i}', method=1, request_path='/callback') for i in range(5)])
        with patch.object(Retention, 'CHILD_BATCH_SIZE', 2):
            self.assertEqual(Retention.delete_batch(self.cutoff), 1)
            self.assertEqual(Retention.delete_batch(self.cutoff), 2)
            self.assertEqual(self.deliveries.count(), 3)
            self.assertTrue(self.traces.filter(id=trace.id).exists())
            self.assertEqual(Retention.cleanup(self.cutoff)['deleted_count'], 5)
        self.assertEqual(self.callbacks.count(), 0)
        self.assertEqual(self.deliveries.count(), 0)
        self.assertEqual(self.resources.count(), 0)
        self.assertEqual(self.traces.count(), 0)

    def test_recent_completed_resource_evidence_is_kept_until_retention_expires(self):
        trace = self.trace('AUTO_RECENT_RESOURCE')
        self.resources.create(case_id=1, trace=trace, step_id=1, parameter_id=1, test_env=0,
            rule_key='rule', rule={}, proof={}, status='cleaned')
        self.assertEqual(Retention.cleanup(self.cutoff)['deleted_count'], 0)
        self.assertEqual(self.resources.count(), 1)

    def test_recent_completed_callback_evidence_is_kept_until_retention_expires(self):
        trace = self.trace('AUTO_RECENT_CALLBACK')
        self.callbacks.create(execution_key='exec', rule_key='callback', case_id=1, mock_config_id=1,
            test_env=0, trace=trace, dependency_digest='digest', correlation_value='value', correlation_key='key',
            deadline=self.cutoff, status='passed', finished_at=timezone.now())
        self.assertEqual(Retention.cleanup(self.cutoff)['deleted_count'], 0)
        self.assertEqual(self.callbacks.count(), 1)
