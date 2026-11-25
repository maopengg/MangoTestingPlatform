from contextlib import ExitStack
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.data_factory.constants import CLEANUP_REPORT_CONTEXT_KEY
from src.apps.data_factory.exceptions import DataFactoryError, DATA_FACTORY_CLEANUP_COORDINATION_FAILED
from src.apps.data_factory.schemas.cleanup_resource import CleanupResourceState, EsCleanupSnapshot, EsCleanupRule
from src.apps.data_factory.services.cleanup.cleanup import DataFactoryCleanup as Cleanup
from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService as Schedule
from src.apps.data_factory.services.recovery.execution_recovery import DataFactoryExecutionRecovery as Recovery


class RecoveryCleanupVerificationTests(SimpleTestCase):
    def setUp(self):
        self.time = timezone.now() - timedelta(days=3)
        self.execution = SimpleNamespace(id=55025, status=3, cleanup_status=2, cleanup_time=timezone.now(),
            error_message='AUTO report detail deleted', save=Mock(), context={
                CLEANUP_REPORT_CONTEXT_KEY: {'parent_case_detail_id': 1351838, 'parent_attempt': 1}})
        self.items = [SimpleNamespace(id=index, cleanup_status=1, cleanup_time=self.time,
            cleanup_resources=CleanupResourceState(sql_cleaned=True).model_dump(mode='json')) for index in range(140)]
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.inline_recovery = Recovery.recover_inline_cleanup.__wrapped__
        self.stack.enter_context(patch.object(Recovery, 'recover_inline_cleanup', return_value=0))
        self.stack.enter_context(patch.object(Recovery, 'reconcile_manual_cleanup_states', return_value={'pending': 0, 'resolved': 0}))
        self.stack.enter_context(patch('src.apps.data_factory.services.recovery.execution_reconciliation.DataFactoryExecutionReconciliation.reconcile', return_value={}))
        self.executions = self.stack.enter_context(patch('src.apps.data_factory.services.recovery.execution_recovery.DataFactoryExecution.objects'))
        self.executions.filter.return_value.exclude.return_value.filter.return_value.distinct.return_value.order_by.return_value.__getitem__.return_value = [self.execution]
        self.stack.enter_context(patch('src.apps.data_factory.services.cleanup.cleanup.CleanupPersistenceService.lock_execution', return_value=self.execution))
        self.item_query = self.stack.enter_context(patch('src.apps.data_factory.services.cleanup.cleanup.DataFactoryExecutionItem.objects'))
        self.item_query.select_for_update.return_value.filter.return_value = self.items
        original = Cleanup.reconcile_verified_cleanup.__wrapped__
        self.stack.enter_context(patch.object(Cleanup, 'reconcile_verified_cleanup', side_effect=lambda execution: original(Cleanup, execution)))
        fail_original = Recovery.fail_unverified_cleanup.__wrapped__
        self.stack.enter_context(patch.object(Recovery, 'fail_unverified_cleanup', side_effect=lambda execution, message:
            fail_original(Recovery, execution, message)))
        self.stack.enter_context(patch('src.apps.data_factory.services.cleanup.cleanup.transaction.on_commit'))
        self.enqueue = self.stack.enter_context(patch.object(Schedule, 'enqueue'))
        self.validate_owner = self.stack.enter_context(patch.object(Schedule, 'validate_report_owner',
            side_effect=DataFactoryError(DATA_FACTORY_CLEANUP_COORDINATION_FAILED, value=('AUTO report detail deleted',))))
        self.fail = self.stack.enter_context(patch.object(Cleanup, 'mark_execution_failed'))

    def test_deleted_report_does_not_turn_140_verified_items_into_cleanup_failure(self):
        result = Recovery.recover()
        self.assertEqual(result['data_factory_recovery_count'], 1)
        self.assertEqual(result['data_factory_recovery_failed_count'], 0)
        self.assertEqual(self.execution.cleanup_status, 1)
        self.assertEqual(self.execution.cleanup_time, self.time)
        self.assertEqual(self.execution.status, 3)
        self.assertEqual(self.execution.error_message, 'AUTO report detail deleted')
        self.assertEqual(len(self.items), 140)
        self.assertTrue(all(item.cleanup_status == 1 for item in self.items))
        self.validate_owner.assert_not_called()
        self.enqueue.assert_not_called()
        self.fail.assert_not_called()
        self.executions.filter.return_value.exclude.assert_called_once_with(cleanup_status=1)
        self.execution.save.assert_called_once()

    def test_report_deletion_with_pending_resource_still_retains_failure_responsibility(self):
        self.items[-1].cleanup_status = 0
        self.items[-1].cleanup_resources['sql_cleaned'] = False
        result = Recovery.recover()
        self.assertEqual(result['data_factory_recovery_failed_count'], 1)
        self.assertEqual(self.execution.cleanup_status, 2)
        self.fail.assert_called_once()
        self.enqueue.assert_not_called()
        self.execution.save.assert_not_called()

    def test_success_flags_without_sql_or_es_evidence_cannot_reconcile_to_success(self):
        self.items[-1].cleanup_resources['sql_cleaned'] = False
        self.assertFalse(Cleanup.cleanup_is_verified(self.items))
        self.items[-1].cleanup_resources = CleanupResourceState(sql_cleaned=True, snapshots=[EsCleanupSnapshot(
            rule=EsCleanupRule(datasource_alias_id=1, index_template='example'), binding_id=1, connection_id=1,
            connection_version='AUTO_VERSION', environment=0, index='example', document_id='1', tenant='7',
            baseline_absent=True)]).model_dump(mode='json')
        self.assertFalse(Cleanup.cleanup_is_verified(self.items))

    def test_completion_during_owner_validation_error_is_rechecked_before_marking_failure(self):
        self.items[-1].cleanup_status = 0
        def owner_changed(*args):
            self.items[-1].cleanup_status = 1
            raise DataFactoryError(DATA_FACTORY_CLEANUP_COORDINATION_FAILED, value=('AUTO report deleted concurrently',))
        self.validate_owner.side_effect = owner_changed
        result = Recovery.recover()
        self.assertEqual(result['data_factory_recovery_count'], 1)
        self.fail.assert_not_called()
        self.enqueue.assert_not_called()

    def test_empty_or_malformed_resource_evidence_is_not_proof_of_cleanup(self):
        self.assertFalse(Cleanup.cleanup_is_verified([]))
        self.items[-1].cleanup_resources = {'snapshots': 'AUTO malformed'}
        self.assertFalse(Cleanup.cleanup_is_verified(self.items))

    def test_unresolved_request_cannot_be_hidden_by_all_successful_item_flags(self):
        self.items[-1].cleanup_resources['uncertain_requests'] = [
            {'request_id': 'AUTO_REQUEST', 'index': 'example', 'document_id': '1'}]
        with patch('src.apps.data_factory.models.SqlExecutionRecord.objects') as records:
            records.filter.return_value.values_list.return_value = [('AUTO_REQUEST', {'outcome_unknown': True})]
            self.assertFalse(Cleanup.cleanup_is_verified(self.items))
            records.filter.return_value.values_list.return_value = [('AUTO_REQUEST', {
                'outcome_unknown': True, 'outcome_resolution': {'basis': 'owned_resource_verified'}})]
            self.assertTrue(Cleanup.cleanup_is_verified(self.items))

    def test_expired_inline_task_does_not_report_failure_after_140_verified_items(self):
        self.executions.filter.return_value.__iter__.return_value = iter([self.execution])
        with patch('src.apps.data_factory.services.recovery.execution_recovery.ExecutorTaskService.expire_inline_cleanup_tasks',
                   return_value=[self.execution.id]):
            failed = self.inline_recovery(Recovery)
        self.assertEqual(failed, 0)
        self.assertEqual(self.execution.cleanup_status, 1)
        self.fail.assert_not_called()
