from contextlib import ExitStack, nullcontext
from datetime import datetime, timezone as datetime_timezone
from types import SimpleNamespace as N
from unittest.mock import Mock, patch

from django.db import OperationalError as ControlDatabaseError
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from pymysql.err import OperationalError
from sqlalchemy.exc import OperationalError as SqlOperationalError

from src.apps.data_factory.enums import DataFactoryGeneratorTypeEnum
from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.schemas.cleanup_resource import (
    CleanupResourceState, EsCleanupRule, EsCleanupSnapshot, EsCleanupCheckpoint,
)
from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService as Errors
from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
from src.apps.data_factory.services.cleanup.cleanup import DataFactoryCleanup as Cleanup
from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService as Resources
from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService as Schedule
from src.apps.data_factory.services.cleanup.cleanup_persistence import CleanupPersistenceService as Persistence
from src.apps.data_factory.services.execution.execution_metadata import DataFactoryExecutionMetadata as Metadata
from src.apps.data_factory.services.execution.runner import DataFactoryRunner as Runner
from src.apps.data_factory.services.recovery.execution_reconciliation import DataFactoryExecutionReconciliation as Reconcile
from src.apps.task_center.services.execution.executor_task import ExecutorTaskService as Tasks


class DeterminedSqlFailureTests(SimpleTestCase):
    def test_1525_is_a_confirmed_rejection_through_driver_wrappers(self):
        driver = OperationalError(1525, 'AUTO_PRIVATE_SQL_VALUE')
        wrapper = SqlOperationalError('AUTO_PRIVATE_SQL', {}, driver)
        for error in (driver, wrapper):
            self.assertTrue(Errors.confirmed_rejection(error))
            reason = Errors.audit_reason(error)
            self.assertIn('1525', reason)
            self.assertIn('字段值', reason)
            self.assertNotIn('AUTO_PRIVATE', reason)
        from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditHandle, SqlExecutionAuditService as Audit
        record = N(request_id='AUTO_REQUEST', source_detail={}, slow_threshold_ms=1000)
        with patch.object(Audit, 'save_completion'), patch.object(Audit, 'notify_slow'):
            Audit.finish_failure(SqlExecutionAuditHandle(record, 0), wrapper, 1)
        self.assertFalse(record.source_detail['outcome_unknown'])
        self.assertIn('1525', record.error_message)

    def test_connection_loss_and_explicit_unknown_override_still_require_review(self):
        for code in (2006, 2013, 2055):
            self.assertFalse(Errors.confirmed_rejection(OperationalError(code, 'AUTO_PRIVATE')))
        wrapped = SqlOperationalError('AUTO_PRIVATE', {}, OperationalError(1525, 'AUTO_PRIVATE'))
        wrapped.connection_invalidated = True
        self.assertFalse(Errors.confirmed_rejection(wrapped))
        error = OperationalError(1525, 'AUTO_PRIVATE')
        error._datasource_outcome_unknown = True
        self.assertFalse(Errors.confirmed_rejection(error))

    @override_settings(MANGO_SERVICE_NAME='scheduler-service')
    def test_control_error_keeps_actual_service_and_safe_driver_metadata(self):
        from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventService
        from src.common.enums.system_error import SystemErrorEventSource
        error = ControlDatabaseError('AUTO_PRIVATE password=DO_NOT_LOG')
        error.__cause__ = OperationalError(1213, 'AUTO_PRIVATE_SQL')
        error.__cause__.sqlstate = '40001'
        with patch.object(SystemErrorEventService, 'record') as record, \
                patch('src.common.logging.log.system.error'):
            Infrastructure.log_reference(error, 'cleanup_dispatch')
        values = record.call_args.kwargs
        self.assertEqual(values['service_name'], 'scheduler-service')
        self.assertEqual(values['source'], SystemErrorEventSource.SCHEDULER)
        self.assertIn('driver_error_number=1213', values['trace'])
        self.assertIn('sqlstate=40001', values['trace'])
        self.assertNotIn('PRIVATE', values['trace'])
        self.assertNotIn('DO_NOT_LOG', str(values))


class ScenePlanReuseTests(SimpleTestCase):
    def setUp(self):
        self.source = N(name='id', platform_type='integer')
        self.target = N(name='parent_id', platform_type='integer')
        self.root_entity, self.child_entity = [N(pk=pk, datafactoryfield_set=Mock()) for pk in (1, 2)]
        self.root_entity.datafactoryfield_set.all.return_value.order_by.return_value = [self.source]
        self.child_entity.datafactoryfield_set.all.return_value.order_by.return_value = [self.target]
        child = N(id=2, name='AUTO_CHILD', entity=self.child_entity, field_overrides={})
        self.root = N(id=1, name='AUTO_ROOT', entity=self.root_entity, field_overrides={})
        self.items = [N(id=i, name=f'AUTO_{i}', child_template_id=2, child_template=child, field_overrides={})
                      for i in range(1, 609)]
        self.root.items = Mock()
        self.query = self.root.items.select_related.return_value.order_by
        self.query.return_value = self.items
        self.rules = {'parent_id': {'generator_type': DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
                                   'generator_config': {'source_node': 'root', 'source_field': 'id'}}}

    def test_608_references_load_scene_and_entity_fields_once_per_execution(self):
        with Metadata.scope():
            for item in self.items:
                result = Runner.prepare_scene_item_overrides(self.root, item, self.rules)
                self.assertEqual(result['parent_id']['generator_config']['alias'], 'AUTO_ROOT')
                self.assertEqual(result['parent_id']['generator_config']['strategy'], 'must_exist')
        self.query.assert_called_once_with('sort', 'id')
        self.assertEqual(self.child_entity.datafactoryfield_set.all.call_count, 1)
        self.assertEqual(self.root_entity.datafactoryfield_set.all.call_count, 1)
        with Metadata.scope():
            Runner.prepare_scene_item_overrides(self.root, self.items[0], self.rules)
        self.assertEqual(self.query.call_count, 2)

    def test_alias_override_does_not_mutate_cached_plan_or_saved_rules(self):
        with Metadata.scope():
            first = Runner.prepare_scene_item_overrides(self.root, self.items[0], self.rules, root_alias='AUTO_OVERRIDE')
            second = Runner.prepare_scene_item_overrides(self.root, self.items[1], self.rules)
        self.assertEqual(first['parent_id']['generator_config']['alias'], 'AUTO_OVERRIDE')
        self.assertEqual(second['parent_id']['generator_config']['alias'], 'AUTO_ROOT')
        self.assertNotIn('alias', self.rules['parent_id']['generator_config'])

    def test_cached_plan_still_rejects_forward_and_ambiguous_references_and_type_mismatch(self):
        for reference in ('item:608', '2'):
            self.rules['parent_id']['generator_config']['source_node'] = reference
            with self.subTest(reference=reference), Metadata.scope(), self.assertRaises(DataFactoryError):
                Runner.prepare_scene_item_overrides(self.root, self.items[0], self.rules)
        self.rules['parent_id']['generator_config']['source_node'] = 'root'
        self.target.platform_type = 'string'
        with Metadata.scope(), self.assertRaises(DataFactoryError):
            Runner.prepare_scene_item_overrides(self.root, self.items[0], self.rules)

    def test_ten_concurrent_executions_do_not_share_same_template_cache(self):
        import threading
        from concurrent.futures import ThreadPoolExecutor
        barrier = threading.Barrier(10)

        def run(number):
            with Metadata.scope():
                value = Metadata.scene_value(1, 'reference_plan', lambda: number)
                barrier.wait(timeout=3)
                self.assertEqual(Metadata.scene_value(1, 'reference_plan', lambda: -1), number)
                return value

        with ThreadPoolExecutor(max_workers=10) as pool:
            self.assertEqual(list(pool.map(run, range(10))), list(range(10)))


class VerifiedFinalizationTests(SimpleTestCase):
    def setUp(self):
        self.execution = N(id=7, status=1, cleanup_status=2, cleanup_time=None, context={},
                           error_message='AUTO_CONTROL_FAILURE', update_time=timezone.now(), save=Mock())
        self.item = N(cleanup_status=1, cleanup_time=timezone.now(), cleanup_resources={'sql_cleaned': True})
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        path = 'src.apps.data_factory.services.recovery.execution_reconciliation.'
        self.stack.enter_context(patch(path+'transaction.atomic', side_effect=lambda: nullcontext()))
        self.committed = self.stack.enter_context(patch(path+'transaction.on_commit'))
        objects = self.stack.enter_context(patch(path+'DataFactoryExecution.objects'))
        objects.select_for_update.return_value.filter.return_value.first.return_value = self.execution
        items = self.stack.enter_context(patch(path+'DataFactoryExecutionItem.objects'))
        items.select_for_update.return_value.filter.return_value = [self.item]
        self.original_settle = Tasks.reconcile_verified_cleanup_task
        self.settle = self.stack.enter_context(patch.object(Tasks, 'reconcile_verified_cleanup_task',
                                                           side_effect=lambda execution_id, verify: verify()))

    def test_failed_parent_with_verified_items_recovers_without_external_reexecution(self):
        self.assertTrue(Reconcile.reconcile_failed_cleanup(self.execution))
        self.assertEqual((self.execution.status, self.execution.cleanup_status), (1, 1))
        self.assertIsNone(self.execution.error_message)
        self.assertEqual(self.execution.context['__platform_execution_reconciliation']['previous_error'], 'AUTO_CONTROL_FAILURE')
        self.assertEqual(self.settle.call_args.args[0], 7)
        self.committed.assert_called_once()

    def test_missing_proof_or_active_task_prevents_reconciliation(self):
        self.item.cleanup_resources = {'sql_cleaned': False}
        self.assertFalse(Reconcile.reconcile_failed_cleanup(self.execution))
        self.settle.assert_called_once()
        self.item.cleanup_resources = {'sql_cleaned': True}
        self.settle.side_effect = None
        self.settle.return_value = False
        self.assertFalse(Reconcile.reconcile_failed_cleanup(self.execution))
        self.execution.save.assert_not_called()
        self.assertEqual(self.execution.cleanup_status, 2)

    def test_latest_failed_task_keeps_original_error_and_does_not_rewrite_finished_at(self):
        task = N(id=8, status='failed', error_message='AUTO_OLD_ERROR', progress_data={'sql_done': True},
                 lease_expires_at=None, finished_at=timezone.now(), save=Mock())
        original_finished = task.finished_at
        with patch('src.apps.task_center.services.execution.executor_task.ExecutorTask.objects') as objects:
            objects.select_for_update.return_value.filter.return_value.order_by.return_value.first.return_value = task
            self.assertTrue(self.original_settle(7, lambda: True))
        self.assertEqual(task.status, 'success')
        self.assertIsNone(task.error_message)
        self.assertEqual(task.progress_data['reconciliation']['previous_error'], 'AUTO_OLD_ERROR')
        self.assertEqual(task.finished_at, original_finished)

    def test_running_or_corrupt_task_cannot_be_reconciled(self):
        task = N(id=8, status='running', error_message='AUTO_OLD_ERROR', progress_data={'sql_done': True}, save=Mock())
        with patch('src.apps.task_center.services.execution.executor_task.ExecutorTask.objects') as objects:
            objects.select_for_update.return_value.filter.return_value.order_by.return_value.first.return_value = task
            self.assertFalse(self.original_settle(7, lambda: True))
            task.status, task.progress_data = 'failed', {'unknown_snapshot': True}
            self.assertFalse(self.original_settle(7, lambda: True))
        task.save.assert_not_called()

    def test_task_lock_precedes_proof_lock_and_failed_proof_never_changes_task(self):
        task = N(status='failed', progress_data={'sql_done': True}, error_message='AUTO_OLD', save=Mock())
        events = []
        def locked_task():
            events.append('task_locked')
            return task
        def rejected_proof():
            events.append('proof_locked')
            return False
        with patch('src.apps.task_center.services.execution.executor_task.ExecutorTask.objects') as objects:
            objects.select_for_update.return_value.filter.return_value.order_by.return_value.first.side_effect = locked_task
            self.assertFalse(self.original_settle(7, rejected_proof))
        self.assertEqual(events, ['task_locked', 'proof_locked'])
        task.save.assert_not_called()

    def test_transient_control_failure_retries_only_finalization_and_is_bounded(self):
        connection = N(in_atomic_block=False, close=Mock())
        for number in (1213, 2013):
            with self.subTest(number=number), \
                    patch.object(Schedule, 'persist_verified_execution', side_effect=[ControlDatabaseError(number, 'AUTO_PRIVATE'), None]) as persist, \
                    patch('src.apps.data_factory.services.cleanup.cleanup_schedule.transaction.get_connection', return_value=connection), \
                    patch.object(Cleanup, 'cleanup_execution') as delete:
                Schedule.finish_verified_execution(7, N(task_id=3), {}, skipped=False)
                self.assertEqual(persist.call_count, 2)
                self.assertFalse(persist.call_args_list[0].kwargs['accept_completed'])
                self.assertTrue(persist.call_args_list[1].kwargs['accept_completed'])
                delete.assert_not_called()
        connection.close.assert_called_once()
        with patch.object(Schedule, 'persist_verified_execution', side_effect=ControlDatabaseError(1213, 'AUTO_PRIVATE')) as persist, \
                patch('src.apps.data_factory.services.cleanup.cleanup_schedule.transaction.get_connection', return_value=connection):
            with self.assertRaises(ControlDatabaseError):
                Schedule.finish_verified_execution(7, N(task_id=3), {}, skipped=False)
        self.assertEqual(persist.call_count, 3)

    def test_completed_commit_with_lost_reply_is_accepted_only_for_same_lease_and_verified_items(self):
        self.execution.cleanup_status = 1
        with patch.object(Persistence, 'lock_execution', return_value=self.execution), \
                patch.object(Tasks, 'cleanup_success_matches_lease', return_value=True), \
                patch.object(Persistence, 'check') as lease_check, \
                patch.object(Tasks, 'finish_cleanup_step') as finish:
            Schedule.persist_verified_execution(7, N(task_id=3), {}, skipped=False, accept_completed=True)
        lease_check.assert_not_called()
        finish.assert_not_called()
        self.execution.save.assert_not_called()

    def test_finalization_failure_cannot_publish_task_success_or_notify(self):
        with patch.object(Persistence, 'lock_execution', return_value=self.execution), \
                patch.object(Persistence, 'check'), \
                patch.object(Persistence, 'save', side_effect=ControlDatabaseError(1213, 'AUTO_PRIVATE')), \
                patch.object(Tasks, 'finish_cleanup_step') as finish:
            with self.assertRaises(ControlDatabaseError):
                Schedule.persist_verified_execution(7, N(task_id=3), {}, skipped=False)
        finish.assert_not_called()
        self.committed.assert_not_called()

    def test_changed_lease_cannot_publish_execution_success(self):
        with patch.object(Persistence, 'lock_execution', return_value=self.execution), \
                patch.object(Persistence, 'check'), patch.object(Persistence, 'save'), \
                patch.object(Tasks, 'finish_cleanup_step', return_value=False):
            with Infrastructure.scope(), self.assertRaises(DataFactoryError):
                Schedule.persist_verified_execution(7, N(task_id=3), {}, skipped=False)
        self.committed.assert_not_called()


class LateEsRecoveryTests(SimpleTestCase):
    def setUp(self):
        self.now = 1800000000.0
        self.rule = EsCleanupRule(datasource_alias_id=1, index_template='example', tenant_path='tenantId',
                                  mode='delete_and_verify', timeout_seconds=3)
        self.snapshot = EsCleanupSnapshot(rule=self.rule, binding_id=1, connection_id=1, connection_version='AUTO',
            environment=0, index='example', requested_index='example', index_uuid='AUTO_UUID',
            document_id='1', tenant='7', baseline_absent=True)
        self.state = CleanupResourceState(sql_cleaned=True, snapshots=[self.snapshot])
        self.item = N(id=11, execution=N(id=7, execution_no='DF_AUTO', project_product_id=1,
            source_type=4, source_id=7, stage=2, context={}), cleanup_resources=self.state.model_dump(mode='json'))
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(Resources, 'validate_snapshot', side_effect=lambda item: Resources.state(item)))
        self.stack.enter_context(patch.object(Resources, 'resolve_binding'))
        self.stack.enter_context(patch('src.apps.data_factory.services.cleanup.cleanup_resource.DatasourceTargetService.resolve'))
        self.stack.enter_context(patch.object(Resources, 'resolve_verified'))
        self.stack.enter_context(patch.object(Persistence, 'save'))
        self.real_sample = Resources.sample
        self.sample = self.stack.enter_context(patch.object(Resources, 'sample', return_value=True))

    def advance(self, seconds, missing=True, generation=0):
        self.now = 1800000000 + seconds
        self.sample.return_value = missing
        return Resources.advance(self.item, generation=generation, task_id=3,
            clock=lambda: datetime.fromtimestamp(self.now, datetime_timezone.utc))

    def test_late_arrival_restarts_full_window_then_requires_two_terminal_samples(self):
        self.advance(0)
        self.advance(2)
        self.assertIsNotNone(self.advance(3, False))
        check = self.item.cleanup_resources['checkpoints'][0]
        self.assertEqual(check['late_recoveries'], 1)
        self.assertTrue(check['late_recovery_pending'])
        self.assertFalse(self.sample.call_args.kwargs['allow_delete'])
        self.advance(3.1, False)
        self.assertTrue(self.sample.call_args.kwargs['allow_delete'])
        self.assertAlmostEqual(self.item.cleanup_resources['checkpoints'][0]['deadline'], 1800000006.1)
        self.advance(5.1)
        self.advance(6.1)
        self.assertFalse(self.item.cleanup_resources['results'])
        self.assertIsNone(self.advance(7.1))
        self.assertTrue(self.item.cleanup_resources['results'][0]['success'])

    def test_persistent_reappearance_exhausts_two_recoveries_instead_of_looping(self):
        self.advance(0)
        for start, final in ((0, 3), (3.1, 6.1)):
            if start:
                self.advance(start, False)
            self.advance(start + 2, False)
            self.advance(final, False)
        self.advance(6.2, False)
        self.advance(8.2, False)
        with self.assertRaises(DataFactoryError):
            self.advance(9.2, False)
        self.assertEqual(self.item.cleanup_resources['checkpoints'][0]['late_recoveries'], 2)
        self.assertFalse(self.item.cleanup_resources['results'])

    def test_generation_change_preserves_recovery_budget_and_restarts_observation(self):
        self.advance(0)
        self.advance(2)
        self.advance(3, False)
        self.advance(20, generation=1)
        check = self.item.cleanup_resources['checkpoints'][0]
        self.assertEqual(check['late_recoveries'], 1)
        self.assertEqual(check['deadline'], 1800000023)
        self.assertFalse(self.item.cleanup_resources['results'])

    def test_verify_only_unknown_requests_and_fixed_compensation_do_not_expand_authority(self):
        from src.apps.data_factory.schemas.cleanup_resource import EsUncertainRequest
        state = CleanupResourceState(sql_cleaned=True)
        self.assertTrue(Resources.can_recover_late_arrival(self.snapshot, state, None, 0))
        self.assertFalse(Resources.can_recover_late_arrival(self.snapshot, state, (1, 1), 0))
        self.assertFalse(Resources.can_recover_late_arrival(self.snapshot, state, None, 2))
        for key, value in (('index_uuid', None), ('requested_index', None), ('baseline_absent', False)):
            self.assertFalse(Resources.can_recover_late_arrival(
                self.snapshot.model_copy(update={key: value}), state, None, 0))
        state.uncertain_requests = [EsUncertainRequest(request_id='AUTO_UNKNOWN', index='example', document_id='1')]
        self.assertFalse(Resources.can_recover_late_arrival(self.snapshot, state, None, 0))
        self.snapshot.rule.mode = 'verify'
        state.uncertain_requests = []
        self.assertFalse(Resources.can_recover_late_arrival(self.snapshot, state, None, 0))

    def test_real_sampling_revalidates_uuid_tenant_and_uses_version_condition_for_late_document(self):
        from src.apps.data_factory.services.datasource.elasticsearch import ElasticsearchDatasourceService as ES
        self.sample.side_effect = self.real_sample
        deleted = []
        document = {'_index': 'example', '_id': '1', '_source': {'tenantId': '7'},
                    '_seq_no': 5, '_primary_term': 2, 'found': True}

        def read(target, index, identity, **kwargs):
            if kwargs.get('delete'):
                self.assertEqual((index, identity), ('example', '1'))
                self.assertEqual((kwargs['expected']['_seq_no'], kwargs['expected']['_primary_term']), (5, 2))
                deleted.append(identity)
                return {'result': 'deleted'}
            return document if self.now >= 1800000003 and not deleted else None

        with patch.object(ES, 'resolve_index', return_value=('example', 'AUTO_UUID')) as resolve, \
                patch.object(ES, 'document', side_effect=read), patch.object(Persistence, 'check'):
            for at in (0, 2, 3, 3.1, 5.1, 6.1, 7.1):
                result = self.advance(at)
        self.assertIsNone(result)
        self.assertEqual(deleted, ['1'])
        self.assertEqual(resolve.call_count, self.sample.call_count)
        self.assertGreaterEqual(resolve.call_count, 6)
        self.assertTrue(self.item.cleanup_resources['results'][0]['success'])

    def test_recovery_rejects_changed_tenant_or_index_without_sending_delete(self):
        from src.apps.data_factory.services.datasource.elasticsearch import ElasticsearchDatasourceService as ES
        self.advance(0)
        self.advance(2)
        self.advance(3, False)
        self.sample.side_effect = self.real_sample
        with patch.object(ES, 'resolve_index', return_value=('example', 'AUTO_UUID')), \
                patch.object(ES, 'document', return_value={'_index': 'example', '_id': '1',
                    '_source': {'tenantId': '8'}, '_seq_no': 5, '_primary_term': 2, 'found': True}) as document, \
                patch.object(Persistence, 'check'):
            with self.assertRaises(DataFactoryError):
                self.advance(3.1)
        self.assertFalse(any(call.kwargs.get('delete') for call in document.call_args_list))
        with patch.object(ES, 'resolve_index', return_value=('example', 'AUTO_REPLACED_UUID')), \
                patch.object(ES, 'document') as document, patch.object(Persistence, 'check'):
            with self.assertRaises(DataFactoryError):
                self.advance(3.1)
        document.assert_not_called()
