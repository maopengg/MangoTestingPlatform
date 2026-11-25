from contextlib import ExitStack, nullcontext, contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.schemas.cleanup_resource import (
    CleanupResourceState, EsCleanupRule, EsCleanupSnapshot, EsCleanupCheckResult, EsCleanupCheckpoint,
)
from src.apps.data_factory.services.cleanup.cleanup_compensation import FactoryCleanupCompensationService as Service
from src.apps.data_factory.services.cleanup.cleanup_history import ResourceCleanupHistoryService as History
from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService as Resources
from src.apps.data_factory.services.cleanup.cleanup import DataFactoryCleanup
from src.apps.data_factory.services.datasource.elasticsearch import ElasticsearchDatasourceService as ES


class CompensationTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id=9)
        snapshot = EsCleanupSnapshot(rule=EsCleanupRule(datasource_alias_id=1, index_template='example', mode='verify'),
            binding_id=2, connection_id=3, connection_version='AUTO_VERSION', environment=0, index='example',
            index_uuid='AUTO_UUID', document_id='1001', tenant='7', baseline_absent=True)
        self.item = SimpleNamespace(id=4, execution_id=5, primary_value='1001', data={'id': 1001, 'tenant_id': 7},
            execution=SimpleNamespace(id=5, project_product_id=6, cleanup_status=1, cleanup_time='AUTO_OLD_TIME', save=Mock()),
            cleanup_status=1, template=SimpleNamespace(cleanup_resources=[]),
            cleanup_resources=CleanupResourceState(snapshots=[snapshot], sql_cleaned=True).model_dump(mode='json'), save=Mock())
        self.request = {'item_id': 4, 'snapshot_index': 0, 'reason': 'AUTO authorized exact recovery'}
        self.document = {'_id': '1001', '_index': 'example', '_seq_no': 7, '_primary_term': 2,
                         '_source': {'tenant_id': '7'}}
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch('src.apps.data_factory.services.sql.factory_sql_execution.DataFactorySqlExecutionService.build_source_context', return_value={}))
        query = Mock()
        query.select_related.return_value.filter.return_value.first.return_value = self.item
        self.stack.enter_context(patch('src.apps.data_factory.services.cleanup.cleanup_compensation.DataFactoryQuerySelector.data_factory_execution_item', return_value=query))
        self.allowed = self.stack.enter_context(patch('src.apps.user.services.authorization.permission.ProjectProductScopeService.has_project_product', return_value=True))
        self.ended = self.stack.enter_context(patch('src.apps.data_factory.services.cleanup.cleanup_compensation.DataFactoryExecutionReconciliation.owner_ended', return_value=True))
        tasks = Mock()
        tasks.filter.return_value.exists.return_value = False
        self.tasks = tasks
        self.stack.enter_context(patch('src.apps.data_factory.services.cleanup.cleanup_compensation.TaskCenterQuerySelector.executor_tasks', return_value=tasks))
        binding = SimpleNamespace(id=2, database_id=3,
            database=SimpleNamespace(update_time=SimpleNamespace(isoformat=lambda: 'AUTO_VERSION')))
        self.stack.enter_context(patch.object(Resources, 'resolve_binding', return_value=binding))
        self.stack.enter_context(patch('src.apps.data_factory.services.cleanup.cleanup_compensation.DatasourceTargetService.resolve'))
        self.stack.enter_context(patch.object(ES, 'resolve_index', return_value=('example', 'AUTO_UUID')))
        self.read = self.stack.enter_context(patch.object(ES, 'document', side_effect=lambda *a, **kw: deepcopy(self.document)))

    def seed_old_success(self):
        state = Resources.state(self.item)
        second = state.snapshots[0].model_copy(deep=True)
        second.document_id = '1002'
        second.document_id_field = second.rule.document_id_field = 'second_id'
        second.row_primary_value = '1001'
        self.item.data['second_id'] = 1002
        state.snapshots.append(second)
        state.results = [EsCleanupCheckResult(snapshot_index=index, index='example', document_id=value.document_id,
            success=True, checked_at='2026-11-18T12:35:28+00:00', attempts=10)
            for index, value in enumerate(state.snapshots)]
        state.checkpoints = [EsCleanupCheckpoint(task_id=25737, snapshot_index=index, generation=0,
            started_at=1, deadline=16, next_check_at=18, absent_count=10, final_count=2, attempts=10)
            for index in range(2)]
        self.item.cleanup_resources = state.model_dump(mode='json')
        return deepcopy(self.item.cleanup_resources)

    @contextmanager
    def authorization_storage(self):
        with patch('src.apps.data_factory.services.cleanup.cleanup_compensation.transaction.atomic', side_effect=nullcontext), \
                patch('src.apps.data_factory.services.cleanup.cleanup_compensation.CleanupPersistenceService.lock_execution',
                      return_value=self.item.execution), \
                patch('src.apps.data_factory.services.cleanup.cleanup_compensation.DataFactoryExecutionItem.objects') as objects, \
                patch.object(History, 'append') as history:
            objects.select_for_update.return_value.get.return_value = self.item
            yield history

    def authorize(self):
        _, _, digest = Service.plan(5, self.request, self.user)
        with self.authorization_storage():
            Service.authorize(5, self.request, self.user, digest)
        return Resources.state(self.item)

    def test_compensation_reopens_only_authorized_resource_and_execution_without_replaying_sql(self):
        original = self.seed_old_success()
        _, _, digest = Service.plan(5, self.request, self.user)
        captured = []
        with self.authorization_storage() as history:
            history.side_effect = lambda *a, **kw: captured.append(deepcopy(kw['item'].cleanup_resources))
            Service.authorize(5, self.request, self.user, digest)
        state = Resources.state(self.item)
        self.assertEqual(state.snapshots[0].model_dump(mode='json'), original['snapshots'][0])
        self.assertTrue(state.sql_cleaned)
        self.assertEqual([value.snapshot_index for value in state.results], [1])
        self.assertEqual(state.results[0].model_dump(mode='json'), original['results'][1])
        self.assertEqual([value.snapshot_index for value in state.checkpoints], [1])
        self.assertEqual(self.item.cleanup_status, 0)
        self.assertEqual(self.item.execution.cleanup_status, 0)
        self.assertIsNone(self.item.execution.cleanup_time)
        self.assertEqual(captured[0]['results'], original['results'])
        self.assertEqual(captured[0]['checkpoints'], original['checkpoints'])
        self.assertEqual(history.call_args.kwargs['authorization_digest'], digest)

    def test_compensation_creates_new_probe_delete_and_full_observation_after_old_success(self):
        self.seed_old_success()
        state = self.authorize()
        self.assertEqual(Resources.pending_compensations(state), {0})
        now = [1800000000.0]
        present = [True]
        def request(*args, **kwargs):
            self.assertEqual(args[2], '1001')
            if kwargs.get('delete'):
                self.assertEqual(kwargs['expected']['_seq_no'], 7)
                self.assertEqual(kwargs['expected']['_primary_term'], 2)
                present[0] = False
                return {'result': 'deleted'}
            return deepcopy(self.document) if present[0] else None
        self.read.reset_mock()
        self.read.side_effect = request
        with patch.object(Resources, 'validate_snapshot', side_effect=Resources.state), \
                patch.object(Resources, 'resolve_verified'), \
                patch('src.apps.data_factory.services.cleanup.cleanup_resource.DatasourceTargetService.resolve'):
            for _ in range(30):
                next_at = Resources.advance(self.item, generation=0, task_id=25763,
                    clock=lambda: datetime.fromtimestamp(now[0], timezone.utc))
                if next_at is None:
                    break
                now[0] = next_at
        self.assertIsNone(next_at)
        state = Resources.state(self.item)
        self.assertEqual(Resources.pending_compensations(state), set())
        check = state.checkpoints[0]
        self.assertEqual(check.task_id, 25763)
        self.assertGreaterEqual(check.final_count, 2)
        self.assertGreaterEqual(now[0] - check.started_at, state.snapshots[0].rule.timeout_seconds)
        result = next(value for value in state.results if value.snapshot_index == 0)
        self.assertEqual(result.compensation_digest, Resources.compensation_digest(state, 0))
        self.assertEqual(sum(bool(value.kwargs.get('delete')) for value in self.read.call_args_list), 1)
        self.assertTrue(state.sql_cleaned)

    def test_reopened_success_enters_resource_phase_and_never_deletes_sql_again(self):
        self.seed_old_success()
        self.authorize()
        self.item.cleanup_strategy = 1
        with patch('src.apps.data_factory.services.cleanup.cleanup.DataFactoryExecution.objects') as executions, \
                patch('src.apps.data_factory.services.cleanup.cleanup.DataFactoryExecutionItem.objects') as items, \
                patch.object(Resources, 'validate_snapshot', side_effect=Resources.state), \
                patch.object(DataFactoryCleanup, 'cleanup_items_in_database_transaction') as sql, \
                patch.object(DataFactoryCleanup, 'validate_cleanup_item') as validate_sql, \
                patch.object(History, 'append') as history, \
                patch('src.apps.data_factory.services.cleanup.cleanup.transaction.on_commit'):
            executions.get.return_value = self.item.execution
            items.select_related.return_value.filter.return_value.order_by.return_value = [self.item]
            result = DataFactoryCleanup.cleanup_execution(5, force_cleanup=True, defer_resources=True)
        self.assertEqual(result['pending'], 1)
        self.assertEqual(result['fail'], 0)
        self.assertNotIn('already_cleaned', result)
        sql.assert_not_called()
        validate_sql.assert_not_called()
        history.assert_called_once()
        self.assertTrue(Resources.state(self.item).sql_cleaned)

    def test_legacy_unindexed_success_is_removed_only_for_the_authorized_target(self):
        self.seed_old_success()
        self.item.cleanup_resources['results'][0]['snapshot_index'] = None
        state = self.authorize()
        self.assertEqual([value.snapshot_index for value in state.results], [1])
        self.assertEqual(Resources.pending_compensations(state), {0})

    def test_cleanup_started_after_preview_rejects_authorization_without_resetting_success(self):
        original = self.seed_old_success()
        _, _, digest = Service.plan(5, self.request, self.user)
        self.tasks.filter.return_value.exists.side_effect = [False, True]
        with self.authorization_storage() as history:
            with self.assertRaises(DataFactoryError):
                Service.authorize(5, self.request, self.user, digest)
            history.assert_not_called()
        self.assertEqual(self.item.cleanup_resources, original)
        self.assertEqual(self.item.cleanup_status, 1)
        self.item.save.assert_not_called()

    def test_old_success_and_checkpoint_cannot_satisfy_new_authorization_even_with_same_task_id(self):
        original = self.seed_old_success()
        state = self.authorize()
        state.results = [EsCleanupCheckResult.model_validate(value) for value in original['results']]
        state.checkpoints = [EsCleanupCheckpoint.model_validate(value) for value in original['checkpoints']]
        self.assertEqual(Resources.pending_compensations(state), {0})
        self.assertTrue(Resources.prepare_observation(state, generation=0, task_id=25737, now=1000))
        self.assertEqual([value.snapshot_index for value in state.results], [1])
        self.assertEqual([value.snapshot_index for value in Resources.pending_observations(state)], [0])
        self.assertEqual(state.checkpoints[0].started_at, 1000)
        self.assertEqual(state.checkpoints[0].final_count, 0)
        self.assertEqual(state.checkpoints[0].compensation_digest, Resources.compensation_digest(state, 0))

    def test_reauthorization_invalidates_previous_compensation_success(self):
        self.seed_old_success()
        state = self.authorize()
        old_digest = Resources.compensation_digest(state, 0)
        state.results.append(EsCleanupCheckResult(snapshot_index=0, index='example', document_id='1001',
            success=True, checked_at='2026-11-18T12:35:28+00:00', attempts=10, compensation_digest=old_digest))
        self.item.cleanup_resources = state.model_dump(mode='json')
        self.item.cleanup_status = self.item.execution.cleanup_status = 1
        self.document['_seq_no'] = 8
        state = self.authorize()
        self.assertNotEqual(Resources.compensation_digest(state, 0), old_digest)
        self.assertEqual(Resources.pending_compensations(state), {0})
        self.assertEqual([value.snapshot_index for value in state.results], [1])

    def test_compensation_delete_version_change_stays_failure_without_reusing_old_success(self):
        self.seed_old_success()
        self.authorize()
        self.document['_seq_no'] = 8
        self.read.reset_mock()
        with patch.object(Resources, 'validate_snapshot', side_effect=Resources.state), \
                patch('src.apps.data_factory.services.cleanup.cleanup_resource.DatasourceTargetService.resolve'):
            with self.assertRaises(DataFactoryError):
                Resources.advance(self.item, generation=0, task_id=25764)
        state = Resources.state(self.item)
        self.assertEqual(Resources.pending_compensations(state), {0})
        self.assertFalse(any(value.kwargs.get('delete') for value in self.read.call_args_list))

    def test_preview_proves_original_identity_and_is_read_only(self):
        before = deepcopy(self.item.cleanup_resources)
        item, grant, digest = Service.plan(5, self.request, self.user)
        self.assertEqual(item.id, 4)
        self.assertEqual((grant.seq_no, grant.primary_term), (7, 2))
        self.assertEqual(len(digest), 64)
        self.assertEqual(self.item.cleanup_resources, before)
        self.item.save.assert_not_called()
        self.assertEqual(self.read.call_count, 2)
        self.assertFalse(any(call.kwargs.get('delete') for call in self.read.call_args_list))

    def test_cross_product_running_owner_and_active_cleanup_fail_before_es_read(self):
        for attribute in ('scope', 'owner', 'task'):
            with self.subTest(attribute=attribute):
                self.allowed.return_value = attribute != 'scope'
                self.ended.return_value = attribute != 'owner'
                self.tasks.filter.return_value.exists.return_value = attribute == 'task'
                self.read.reset_mock()
                with self.assertRaises(DataFactoryError):
                    Service.plan(5, self.request, self.user)
                self.read.assert_not_called()

    def test_arbitrary_document_tenant_or_force_flags_are_not_accepted(self):
        for field in ('document_id', 'tenant', 'skip_ownership', 'index'):
            with self.subTest(field=field), self.assertRaises(DataFactoryError):
                Service.plan(5, {**self.request, field: 'AUTO_other'}, self.user)
        self.read.assert_not_called()

    def test_foreign_tenant_missing_uuid_or_unverified_sql_cannot_be_authorized(self):
        for field, value in (('tenant', '8'), ('index_uuid', None), ('sql_cleaned', False)):
            before = deepcopy(self.item.cleanup_resources)
            if field == 'sql_cleaned':
                self.item.cleanup_resources[field] = value
            else:
                self.item.cleanup_resources['snapshots'][0][field] = value
            with self.subTest(field=field), self.assertRaises(DataFactoryError):
                Service.plan(5, self.request, self.user)
            self.item.cleanup_resources = before

    def test_preview_version_changes_invalidate_target_digest(self):
        _, _, before = Service.plan(5, self.request, self.user)
        self.document['_seq_no'] = 8
        _, _, after = Service.plan(5, self.request, self.user)
        self.assertNotEqual(before, after)

    def test_authorization_appends_evidence_without_changing_original_snapshot(self):
        _, _, digest = Service.plan(5, self.request, self.user)
        before = deepcopy(self.item.cleanup_resources['snapshots'])
        with patch('src.apps.data_factory.services.cleanup.cleanup_compensation.transaction.atomic', side_effect=nullcontext), \
                patch('src.apps.data_factory.services.cleanup.cleanup_compensation.CleanupPersistenceService.lock_execution'), \
                patch('src.apps.data_factory.services.cleanup.cleanup_compensation.DataFactoryExecutionItem.objects') as objects, \
                patch.object(History, 'append') as history:
            objects.select_for_update.return_value.get.return_value = self.item
            Service.authorize(5, self.request, self.user, digest)
        self.assertEqual(self.item.cleanup_resources['snapshots'], before)
        self.assertEqual(len(self.item.cleanup_resources['compensations']), 1)
        self.assertEqual(history.call_args.kwargs['authorization_digest'], digest)
        self.item.save.assert_called_once()

    def test_changed_target_cannot_be_authorized_with_old_confirmation(self):
        _, _, digest = Service.plan(5, self.request, self.user)
        self.document['_seq_no'] = 8
        with patch('src.apps.data_factory.services.cleanup.cleanup_compensation.transaction.atomic', side_effect=nullcontext), \
                patch('src.apps.data_factory.services.cleanup.cleanup_compensation.CleanupPersistenceService.lock_execution'), \
                patch('src.apps.data_factory.services.cleanup.cleanup_compensation.DataFactoryExecutionItem.objects'), \
                patch.object(History, 'append') as history, self.assertRaises(DataFactoryError):
            Service.authorize(5, self.request, self.user, digest)
        history.assert_not_called()
        self.item.save.assert_not_called()
