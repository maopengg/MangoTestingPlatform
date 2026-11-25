from copy import deepcopy
from datetime import datetime, timezone as dt_timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
import io
import json
from urllib.error import HTTPError

from django.test import SimpleTestCase

from src.apps.data_factory.enums.cleanup_resource import EsCleanupModeEnum
from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.formatters import cleanup_diagnostics, preview_cleanup_rules
from src.apps.data_factory.schemas.cleanup_resource import (
    CleanupResourceState, EsCleanupRule, EsCleanupSnapshot, EsCleanupCheckResult, EsCleanupCompensation,
)
from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService as Resources
from src.apps.data_factory.services.cleanup.cleanup_history import ResourceCleanupHistoryService as History
from src.apps.data_factory.services.datasource.elasticsearch import ElasticsearchDatasourceService as ES
from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService as Errors
from src.apps.auto_api.schemas.resource_cleanup import ApiResourceCleanupRule
from src.apps.auto_api.tests.test_resource_cleanup import rule_data


class EsLifecycleTests(SimpleTestCase):
    @staticmethod
    def conflict(status=409, error_type='version_conflict_engine_exception'):
        raw = HTTPError('https://example.com/example_7/_doc/1001', status, 'conflict', {},
            io.BytesIO(json.dumps({'error': {'type': error_type, 'reason': 'AUTO concurrent update'}}).encode()))
        try:
            Errors.raise_elasticsearch_http_error(SimpleNamespace(), raw)
        except DataFactoryError as error:
            return error

    def setUp(self):
        self.now = 1800000000.0
        self.rule = EsCleanupRule(datasource_alias_id=1, index_template='example_{tenant}',
            timeout_seconds=15, poll_seconds=1, mode='delete_and_verify')
        self.snapshot = EsCleanupSnapshot(rule=self.rule, binding_id=2, connection_id=3,
            connection_version='AUTO_VERSION', environment=0, index='example_7', document_id='1001',
            tenant='7', baseline_absent=True)
        self.item = SimpleNamespace(id=4, execution_id=5, execution=SimpleNamespace(id=5, project_product_id=6),
            cleanup_resources=CleanupResourceState(snapshots=[self.snapshot], sql_cleaned=True).model_dump(mode='json'),
            save=Mock())

    def clock(self):
        return datetime.fromtimestamp(self.now, dt_timezone.utc)

    def test_only_structured_version_conflict_can_be_revalidated(self):
        self.assertTrue(Errors.is_elasticsearch_version_conflict(self.conflict()))
        for error in (self.conflict(403), self.conflict(error_type='other_conflict'),
                      RuntimeError('409 version_conflict_engine_exception')):
            self.assertFalse(Errors.is_elasticsearch_version_conflict(error))

    def test_audit_failure_or_unknown_outcome_cannot_be_hidden_by_conflict_recovery(self):
        for flag, value in (('_datasource_audit_failure_code', 34190),
                            ('_datasource_outcome_unknown', True),
                            ('_datasource_unknown_permit', ('a' * 32, 'b' * 32))):
            error = self.conflict()
            setattr(error, flag, value)
            self.assertFalse(Errors.is_elasticsearch_version_conflict(error))

    def test_conflict_reschedules_without_success_or_unknown_occupancy(self):
        def conflict(*args, **kwargs):
            raise self.conflict()
        next_at = self.advance(conflict)
        state = Resources.state(self.item)
        self.assertEqual(state.checkpoints[0].version_conflicts, 1)
        self.assertEqual(state.checkpoints[0].absent_count, 0)
        self.assertEqual(state.unknown_permits, [])
        self.assertEqual(state.results, [])
        for _ in range(20):
            self.now = next_at
            next_at = self.advance(lambda *a, **kw: True)
            if next_at is None:
                break
        state = Resources.state(self.item)
        self.assertTrue(state.results[0].success)
        self.assertGreaterEqual(state.checkpoints[0].final_count, 2)
        self.assertGreaterEqual(self.now - state.checkpoints[0].started_at, 15)

    def test_conflicts_remain_bounded_across_worker_observation_restart(self):
        def conflict(*args, **kwargs):
            raise self.conflict()
        for _ in range(3):
            next_at = self.advance(conflict)
            self.now = next_at + 100
        with self.assertRaises(DataFactoryError):
            self.advance(conflict)
        state = Resources.state(self.item)
        self.assertEqual(state.checkpoints[0].version_conflicts, 4)
        self.assertFalse(state.results)

    def test_pinned_compensation_does_not_automatically_reauthorize_conflict(self):
        with patch.object(Resources, 'effective_snapshot', return_value=(self.snapshot, (7, 2))):
            with self.assertRaises(DataFactoryError):
                self.advance(lambda *a, **kw: (_ for _ in ()).throw(self.conflict()))
        self.assertEqual(Resources.state(self.item).checkpoints[0].version_conflicts, 1)

    def test_resampled_document_must_still_belong_to_original_tenant(self):
        document = {'_id': '1001', '_index': 'example_7', '_seq_no': 8, '_primary_term': 2,
                    '_source': {'tenant_id': '8'}}
        with patch.object(ES, 'document', return_value=document) as request:
            with self.assertRaises(DataFactoryError):
                Resources.sample(self.snapshot, Mock(), allow_delete=True)
        self.assertEqual(request.call_count, 1)

    def advance(self, sample):
        with patch.object(Resources, 'validate_snapshot', side_effect=Resources.state), \
                patch.object(Resources, 'resolve_binding'), \
                patch('src.apps.data_factory.services.cleanup.cleanup_resource.DatasourceTargetService.resolve'), \
                patch.object(Resources, 'sample', side_effect=sample), \
                patch('src.apps.data_factory.services.sql.factory_sql_execution.DataFactorySqlExecutionService.build_source_context', return_value={}), \
                patch.object(Resources, 'resolve_verified'):
            return Resources.advance(self.item, generation=0, task_id=1, clock=self.clock)

    def test_slow_successful_probe_does_not_restart_full_window_forever(self):
        def sample(*args, **kwargs):
            self.now += 12
            return True
        for _ in range(8):
            next_at = self.advance(sample)
            if next_at is None:
                break
            self.now = next_at
        self.assertIsNone(next_at)
        state = Resources.state(self.item)
        self.assertEqual(state.checkpoints[0].restart_count, 0)
        self.assertGreaterEqual(state.checkpoints[0].processing_seconds, 36)
        self.assertGreaterEqual(state.checkpoints[0].final_count, 2)
        self.assertTrue(state.results[0].success)

    def test_real_dispatch_gap_restarts_window_and_never_counts_downtime(self):
        self.advance(lambda *a, **kw: True)
        self.now += 100
        self.assertIsNotNone(self.advance(lambda *a, **kw: True))
        state = Resources.state(self.item)
        self.assertEqual(state.checkpoints[0].deadline, self.now + 15)
        self.assertEqual(state.checkpoints[0].restart_count, 1)
        self.assertEqual(state.results, [])

    def test_completed_resource_not_replayed_when_other_resource_recovers(self):
        state = Resources.state(self.item)
        state.snapshots.append(self.snapshot.model_copy(update={'index': 'example_other'}))
        state.results.append(EsCleanupCheckResult(snapshot_index=0, index='example_7',
            document_id='1001', success=True, checked_at=self.clock().isoformat(), attempts=5))
        Resources.prepare_observation(state, generation=2, task_id=9, now=self.now)
        self.assertEqual([value.snapshot_index for value in Resources.pending_observations(state)], [1])
        self.assertEqual(len(state.results), 1)

    def test_factory_and_api_index_rules_share_tenant_only_and_fixed_contract(self):
        for index in ('{tenant}', 'example_{tenant}', 'example'):
            self.assertEqual(EsCleanupRule(datasource_alias_id=1, index_template=index).index_template,
                ApiResourceCleanupRule.model_validate(rule_data(index_template=index)).index_template)

    def test_preview_is_explicitly_not_environment_validation_and_does_not_guess_ids(self):
        result = preview_cleanup_rules([self.rule.model_dump(mode='json')], '_id', {'tenant_id': 7})[0]
        self.assertFalse(result['environment_checked'])
        self.assertIsNone(result['document_id'])
        self.assertEqual(result['pending_fields'], ['_id'])
        self.assertEqual(result['resolution'], 'deferred_until_execution')

    def test_unknown_residual_count_is_not_reported_as_zero(self):
        result = cleanup_diagnostics(self.item.cleanup_resources)
        self.assertEqual(result['sql_residual_count'], 0)
        self.assertIsNone(result['es_resources'][0]['residual_count'])

    def test_compensation_preserves_snapshot_and_rejects_modified_original(self):
        state = Resources.state(self.item)
        original = deepcopy(state.snapshots[0].model_dump(mode='json'))
        state.compensations.append(EsCleanupCompensation(snapshot_index=0, snapshot_digest=History.digest(original),
            operator_id=1, authorized_at=self.clock().isoformat(), reason='AUTO authorized recovery',
            seq_no=7, primary_term=2))
        effective, version = Resources.effective_snapshot(self.item, state, 0)
        self.assertEqual(version, (7, 2))
        self.assertEqual(effective.rule.mode, EsCleanupModeEnum.DELETE_AND_VERIFY)
        self.assertEqual(state.snapshots[0].model_dump(mode='json'), original)
        state.snapshots[0].tenant = '8'
        with self.assertRaises(DataFactoryError):
            Resources.effective_snapshot(self.item, state, 0)

    def test_compensation_version_change_does_not_send_delete(self):
        document = {'_id': '1001', '_index': 'example_7', '_seq_no': 8, '_primary_term': 2,
                    '_source': {'tenant_id': '7'}}
        with patch.object(ES, 'document', return_value=document) as request:
            with self.assertRaises(DataFactoryError):
                Resources.sample(self.snapshot, Mock(), allow_delete=True, expected_version=(7, 2))
        self.assertEqual(request.call_count, 1)

    def test_verify_mode_never_deletes_even_when_document_exists(self):
        self.snapshot.rule.mode = EsCleanupModeEnum.VERIFY
        document = {'_id': '1001', '_source': {'tenant_id': '7'}}
        with patch.object(ES, 'document', return_value=document) as request:
            self.assertFalse(Resources.sample(self.snapshot, Mock(), allow_delete=True))
        self.assertEqual(request.call_count, 1)

    def test_pre_sql_ownership_rejection_happens_before_any_delete(self):
        state = Resources.state(self.item)
        state.sql_cleaned = False
        with patch.object(Resources, 'resolve_binding'), \
                patch('src.apps.data_factory.services.cleanup.cleanup_resource.DatasourceTargetService.resolve'), \
                patch.object(ES, 'document', return_value={'_id': '1001', '_source': {}}) as document:
            with self.assertRaises(DataFactoryError):
                Resources.validate_before_sql(self.item, state)
        self.assertEqual(document.call_count, 1)
        self.assertFalse(state.sql_cleaned)

    def test_forced_retry_does_not_replay_verified_items(self):
        from src.apps.data_factory.enums.cleanup import DataFactoryCleanupStatusEnum as Status
        from src.apps.data_factory.services.cleanup.cleanup import DataFactoryCleanup
        execution = SimpleNamespace(id=5, cleanup_status=Status.FAIL.value, save=Mock())
        self.item.cleanup_status = Status.SUCCESS.value
        with patch('src.apps.data_factory.services.cleanup.cleanup.DataFactoryExecution.objects') as executions, \
                patch('src.apps.data_factory.services.cleanup.cleanup.DataFactoryExecutionItem.objects') as items, \
                patch('src.apps.data_factory.services.cleanup.cleanup.CleanupPersistenceService.save'), \
                patch('src.apps.data_factory.services.cleanup.cleanup.transaction.on_commit'), \
                patch.object(Resources, 'validate_snapshot') as validate, \
                patch.object(History, 'append') as history:
            executions.get.return_value = execution
            items.select_related.return_value.filter.return_value.order_by.return_value = [self.item]
            result = DataFactoryCleanup.cleanup_execution(5, force_cleanup=True, defer_resources=True)
        self.assertTrue(result['already_cleaned'])
        validate.assert_not_called()
        history.assert_not_called()

    def test_history_keeps_full_failure_and_persisted_observation(self):
        from src.apps.data_factory.enums.cleanup_history import ResourceCleanupEventEnum
        self.advance(lambda *a, **kw: True)
        message = 'AUTO precise failure ' * 300
        with patch('src.apps.data_factory.services.cleanup.cleanup_history.CleanupPersistenceService.write',
                   side_effect=lambda callback: callback()), \
                patch.object(History, 'append_factory') as events:
            History.append(ResourceCleanupEventEnum.FAILED, item=self.item, message=message)
        evidence = events.call_args.args[1]['evidence']
        self.assertEqual(evidence['message'], message)
        self.assertEqual(evidence['checkpoints'][0]['attempts'], 1)
        self.assertEqual(evidence['results'], [])
