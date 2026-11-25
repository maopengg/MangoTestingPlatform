from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.data_factory.services.recovery.execution_reconciliation import DataFactoryExecutionReconciliation as Reconcile
from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService as Resources
from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService as Schedule
from src.apps.data_factory.constants import EXECUTION_OWNER_CONTEXT_KEY, EXECUTION_RECONCILIATION_CONTEXT_KEY
from src.apps.data_factory.schemas.cleanup_resource import (
    CleanupResourceState, EsCleanupSnapshot, EsCleanupRule, EsCleanupCheckResult,
)


class ExecutionStateReconciliationTests(SimpleTestCase):
    def setUp(self):
        self.execution = SimpleNamespace(id=17, status=1, cleanup_status=1, update_time=timezone.now(),
            create_time=timezone.now(), context={}, error_message='AUTO old cleanup error', save=Mock())
        self.item = SimpleNamespace(cleanup_status=1)
        self.state = CleanupResourceState(sql_cleaned=True)

    def test_only_full_owned_verification_allows_error_convergence(self):
        snapshot = EsCleanupSnapshot(rule=EsCleanupRule(datasource_alias_id=1, index_template='example'),
            binding_id=1, connection_id=1, connection_version='AUTO_VERSION', environment=0,
            index='example', document_id='1', tenant='7', baseline_absent=True)
        self.state.snapshots = [snapshot]
        self.state.sql_cleaned = True
        self.state.results = [EsCleanupCheckResult(snapshot_index=0, success=True, index='example', document_id='1',
            checked_at=timezone.now().isoformat(), attempts=2)]
        with patch.object(Resources, 'state', return_value=self.state):
            self.assertTrue(Reconcile.fully_verified([self.item]))
            self.assertFalse(Reconcile.fully_verified([]))
            for field, invalid in [('sql_cleaned', False), ('unknown_permits', [Mock()]), ('results', [])]:
                with self.subTest(field=field), patch.object(self.state, field, invalid):
                    self.assertFalse(Reconcile.fully_verified([self.item]))
            self.state.results[0].document_id = 'foreign'
            self.assertFalse(Reconcile.fully_verified([self.item]))

    def test_cleared_error_is_archived_and_failed_creation_is_excluded(self):
        path = 'src.apps.data_factory.services.recovery.execution_reconciliation.'
        with patch(path+'transaction.atomic', return_value=nullcontext()), \
                patch(path+'DataFactoryExecution.objects') as executions, \
                patch(path+'DataFactoryExecutionItem.objects') as items, \
                patch(path+'transaction.on_commit') as committed, \
                patch.object(Reconcile, 'fully_verified', return_value=True):
            executions.select_for_update.return_value.filter.return_value.first.return_value = self.execution
            items.filter.return_value = [self.item]
            self.assertTrue(Reconcile.reconcile_cleaned(self.execution))
        self.assertIsNone(self.execution.error_message)
        evidence = self.execution.context[EXECUTION_RECONCILIATION_CONTEXT_KEY]
        self.assertEqual(evidence['previous_error'], 'AUTO old cleanup error')
        self.assertEqual(executions.select_for_update.return_value.filter.call_args.kwargs['status'], 1)
        committed.assert_called_once()

    def test_empty_execution_requires_confirmed_owner_and_is_never_marked_clean(self):
        path = 'src.apps.data_factory.services.recovery.execution_reconciliation.'
        self.execution.status = 3
        self.execution.cleanup_status = 0
        with patch.object(Reconcile, 'owner_ended', return_value=False):
            self.assertFalse(Reconcile.reconcile_empty(self.execution))
            self.execution.save.assert_not_called()
        with patch.object(Reconcile, 'owner_ended', return_value=True), \
                patch(path+'transaction.atomic', return_value=nullcontext()), \
                patch(path+'DataFactoryExecution.objects') as executions, \
                patch(path+'DataFactoryExecutionItem.objects') as items:
            executions.select_for_update.return_value.filter.return_value.first.return_value = self.execution
            items.filter.return_value.exists.return_value = False
            self.assertTrue(Reconcile.reconcile_empty(self.execution))
        self.assertEqual((self.execution.status, self.execution.cleanup_status), (0, 0))
        self.assertIn('需核查', self.execution.error_message)

    def test_changed_or_live_execution_cannot_be_converged_by_old_snapshot(self):
        path = 'src.apps.data_factory.services.recovery.execution_reconciliation.'
        with patch.object(Reconcile, 'owner_ended', return_value=True), \
                patch(path+'transaction.atomic', return_value=nullcontext()), \
                patch(path+'DataFactoryExecution.objects') as executions:
            executions.select_for_update.return_value.filter.return_value.first.return_value = None
            self.assertFalse(Reconcile.reconcile_empty(self.execution))
        self.execution.save.assert_not_called()
        self.assertEqual(executions.select_for_update.return_value.filter.call_args.kwargs['update_time'],
                         self.execution.update_time)

    def test_missing_or_invalid_identity_is_review_only_not_age_based_termination(self):
        self.assertFalse(Reconcile.owner_ended(self.execution))
        self.execution.context[EXECUTION_OWNER_CONTEXT_KEY] = {'process_token': 'forged'}
        self.assertFalse(Reconcile.owner_ended(self.execution))

    def test_execution_context_replaces_forged_process_identity(self):
        with patch('src.apps.system.services.runtime_center.process_identity.RuntimeProcessIdentity.current',
                   return_value={'process_token': 'AUTO_REAL', 'process_started_at': '2026-11-15T10:00:00'}):
            result = Schedule.execution_context({EXECUTION_OWNER_CONTEXT_KEY: {'process_token': 'forged'}})
        self.assertEqual(result[EXECUTION_OWNER_CONTEXT_KEY]['process_token'], 'AUTO_REAL')

    def test_unknown_requests_and_oversized_original_evidence_are_not_silently_cleared(self):
        with patch.object(Resources, 'state', return_value=self.state):
            self.state.unknown_permits = [Mock()]
            self.assertFalse(Reconcile.fully_verified([self.item]))
            self.state.unknown_permits = []
        self.state.uncertain_requests = [SimpleNamespace(request_id='AUTO_UNKNOWN')]
        with patch.object(Resources, 'state', return_value=self.state), \
                patch('src.apps.data_factory.models.SqlExecutionRecord.objects') as records:
            records.filter.return_value.values_list.return_value = [('AUTO_UNKNOWN', {'outcome_unknown': True})]
            self.assertFalse(Reconcile.fully_verified([self.item]))
            records.filter.return_value.values_list.return_value = [('AUTO_UNKNOWN', {
                'outcome_unknown': True, 'outcome_resolution': {'basis': 'owned_resource_verified'}})]
            self.assertTrue(Reconcile.fully_verified([self.item]))
        self.execution.error_message = 'x' * 1001
        self.assertFalse(Reconcile.save_evidence(self.execution, 'AUTO_REASON'))
        self.assertEqual(len(self.execution.error_message), 1001)


class WorkerIncidentRecoveryTests(SimpleTestCase):
    def test_only_confirmed_replacement_without_old_running_details_can_close_incident(self):
        from src.apps.data_factory.services.recovery.health_incident import DatasourceHealthIncidentService as Health
        state = SimpleNamespace(scope='api-worker:example-worker:AUTO_OLD', opened_at=1.0)
        with patch('src.apps.system.services.runtime_center.heartbeat.ServiceHeartbeatService.get_online_instances',
                   return_value=[SimpleNamespace(instance_name='example-worker')]), \
                patch('src.apps.task_center.services.execution.worker_recovery.ApiWorkerRecoveryService.replacement_confirmed',
                      return_value=True) as replacement, \
                patch('src.apps.test_center.selectors.querysets.TestCenterQuerySelector.test_suite_details') as details:
            details.return_value.filter.return_value.exists.return_value = False
            self.assertTrue(Health.replaced_worker_ended(state))
            details.return_value.filter.return_value.exists.return_value = True
            self.assertFalse(Health.replaced_worker_ended(state))
            replacement.return_value = False
            self.assertFalse(Health.replaced_worker_ended(state))
        self.assertEqual(details.return_value.filter.call_args.kwargs[
            'summary_data__meta__worker_owner__process_token'], 'AUTO_OLD')
