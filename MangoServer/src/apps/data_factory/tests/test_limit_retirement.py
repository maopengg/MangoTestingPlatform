import json
from copy import deepcopy
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from mangotools.enums import CacheValueTypeEnum
from pydantic import ValidationError

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.services.recovery.limit_retirement import DatasourceLimitRetirementService as Retirement
from src.apps.data_factory.tests.test_datasource_performance import AtomicMemoryStore


class LimitRetirementTests(SimpleTestCase):
    def setUp(self):
        self.key = 'group:' + 'a' * 32 + ':control'
        self.owner = 'b' * 32
        self.permit = {'owner': self.owner, 'process': 'old-worker', 'lane': 'normal',
                       'kind': 'operation', 'state': 'suspect', 'expires_at': 1,
                       'audit_record_id': 7, 'created_at': 0}
        self.original = {'version': 1, 'tokens': 3, 'waiters': {},
                         'permits': {self.owner: self.permit}}
        self.store = AtomicMemoryStore()
        self.store.set(self.key, self.original)
        self.config = SimpleNamespace(value=json.dumps({'version': 1, 'mysql': {'connections': 20}}),
                                      value_type=CacheValueTypeEnum.DICT.value)
        self.row = SimpleNamespace(key=self.key, value={'data': self.original})
        queryset = Mock()
        queryset.filter.return_value.select_for_update.return_value = [self.row]
        for guard in (
            patch('src.apps.data_factory.services.recovery.limit_retirement.ConfigurationSelector.locked_datasource_policy',
                  return_value=self.config),
            patch('src.apps.data_factory.services.recovery.limit_retirement.RuntimeKV.namespace', return_value=self.store),
            patch('src.apps.data_factory.services.recovery.limit_retirement.RuntimeKVSelector.active', return_value=queryset),
            patch('src.apps.data_factory.services.recovery.limit_retirement.ServiceHeartbeatService.get_online_instances',
                  return_value=[]),
            patch('src.apps.data_factory.services.recovery.limit_retirement.CacheDataService.replace_retired_datasource_policy'),
        ):
            guard.start()
            self.addCleanup(guard.stop)

    def run_retirement(self, apply=False):
        return Retirement.run.__func__.__wrapped__(Retirement, apply=apply)

    def test_preview_never_changes_config_or_runtime(self):
        from src.apps.data_factory.services.recovery.limit_retirement import CacheDataService
        result = self.run_retirement()
        self.assertFalse(result['applied'])
        self.assertEqual(result['preserved_permits'], 1)
        self.assertEqual(self.store.get(self.key), self.original)
        CacheDataService.replace_retired_datasource_policy.assert_not_called()

    def test_online_old_process_refuses_apply_before_any_mutation(self):
        with patch('src.apps.data_factory.services.recovery.limit_retirement.ServiceHeartbeatService.get_online_instances',
                   return_value=['old-worker']), self.assertRaises(DataFactoryError):
            self.run_retirement(apply=True)
        self.assertEqual(self.store.values, {self.key: self.original})

    def test_apply_archives_original_and_preserves_unknown_operation_on_repeat(self):
        self.run_retirement(apply=True)
        self.assertEqual(self.store.get('retired:' + self.key), self.original)
        state = self.store.get(self.key)
        self.assertEqual(state['version'], 2)
        self.assertEqual(state['permits'][self.owner]['audit_record_id'], 7)
        self.assertEqual(state['permits'][self.owner]['state'], 'suspect')
        self.assertNotIn('tokens', state)
        self.row.value = {'data': state}
        self.run_retirement(apply=True)
        self.assertEqual(self.store.get('retired:' + self.key), self.original)
        self.assertEqual(self.store.get(self.key), state)

    def test_changed_snapshot_cannot_be_overwritten(self):
        with self.assertRaises(DataFactoryError):
            Retirement.replace_state({'version': 2, 'permits': {}}, self.original, {})

    def test_legacy_empty_permit_scopes_preserve_all_evidence_without_mutating_input(self):
        for version in (None, 1):
            for kind in ('connection', 'operation'):
                for state in ('active', 'suspect'):
                    with self.subTest(version=version, kind=kind, state=state):
                        original = deepcopy(self.original)
                        if version is None:
                            original.pop('version')
                        permit = original['permits'][self.owner]
                        permit.update(kind=kind, state=state, scopes=[], slots=2,
                            case_detail_id=11, case_attempt=3, unknown_since=2,
                            recovery_checked_at=3, mysql_session={
                                'server_uuid': '12345678-1234-1234-1234-123456789abc',
                                'session_id': 123, 'target_key': 'a' * 40,
                                'account_digest': 'c' * 64})
                        before = deepcopy(original)
                        converted = Retirement.state(original)['permits'][self.owner]
                        self.assertEqual(original, before)
                        self.assertNotIn('scopes', converted)
                        for key, expected in permit.items():
                            if key != 'scopes':
                                self.assertEqual(converted[key], expected)

    def test_legacy_empty_scopes_preview_apply_and_repeat_keep_original_archive(self):
        from src.apps.data_factory.services.recovery.limit_retirement import CacheDataService
        self.permit['scopes'] = []
        self.store.set(self.key, self.original)
        before = deepcopy(self.original)
        result = self.run_retirement()
        self.assertEqual(result['preserved_permits'], 1)
        self.assertEqual(self.store.values, {self.key: before})
        self.assertEqual(self.row.value['data'], before)
        CacheDataService.replace_retired_datasource_policy.assert_not_called()
        self.run_retirement(apply=True)
        self.assertEqual(self.store.get('retired:' + self.key), before)
        self.assertEqual(self.store.get('retired:policy:v1'), json.loads(self.config.value))
        state = deepcopy(self.store.get(self.key))
        self.assertNotIn('scopes', state['permits'][self.owner])
        self.assertEqual(state['permits'][self.owner]['state'], 'suspect')
        self.assertEqual(state['permits'][self.owner]['audit_record_id'], 7)
        self.row.value = {'data': state}
        self.run_retirement(apply=True)
        self.assertEqual(self.store.get('retired:' + self.key), before)
        self.assertEqual(self.store.get(self.key), state)

    def test_nonempty_or_malformed_permit_scopes_abort_before_any_write(self):
        from src.apps.data_factory.services.recovery.limit_retirement import CacheDataService
        for scopes in (['tenant-one'], {'tenant': 'one'}, {}, None, '', False):
            with self.subTest(scopes=scopes):
                self.permit['scopes'] = scopes
                self.store.set(self.key, self.original)
                before = deepcopy(self.store.values)
                with self.assertRaises(DataFactoryError):
                    self.run_retirement(apply=True)
                self.assertEqual(self.store.values, before)
        CacheDataService.replace_retired_datasource_policy.assert_not_called()

    def test_empty_scopes_do_not_hide_unknown_evidence_or_invalid_v2_fields(self):
        self.permit['scopes'] = []
        self.permit['unrecognized_evidence'] = {'cleanup': 'must-not-discard'}
        self.store.set(self.key, self.original)
        with self.assertRaises(ValidationError):
            self.run_retirement(apply=True)
        self.assertEqual(self.store.values, {self.key: self.original})
        del self.permit['unrecognized_evidence']
        with self.assertRaises(ValidationError):
            Retirement.state({**self.original, 'version': 2})

    def test_unknown_fields_and_oversized_evidence_are_not_dropped(self):
        with self.assertRaises(ValidationError):
            Retirement.state({**self.original, 'unrecognized_evidence': True})
        self.store.policy['max_bytes'] = 100
        with self.assertRaises(DataFactoryError):
            self.run_retirement(apply=True)
        self.assertEqual(self.store.values, {self.key: self.original})


class ResourceOutcomeResolutionTests(SimpleTestCase):
    def test_confirmation_is_exact_and_keeps_original_timeout(self):
        from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService as Audit
        record = SimpleNamespace(request_id='request-one', status='failed',
            error_message='response timeout', source_detail={'outcome_unknown': True})
        manager = Mock()
        manager.using.return_value.select_for_update.return_value.filter.return_value.exclude.return_value = [record]
        with patch('src.apps.data_factory.services.sql.sql_execution_audit.SqlExecutionRecord.objects', manager), \
                patch.object(Audit, 'database_alias', return_value='unit'), \
                patch('django.db.transaction.atomic', side_effect=lambda **kw: nullcontext()), \
                patch.object(Audit, 'save_completion') as saved:
            Audit.confirm_resource_requests(['request-one'])
        manager.using.return_value.select_for_update.return_value.filter.assert_called_once_with(
            request_id__in={'request-one'}, source_detail__outcome_unknown=True)
        manager.using.return_value.select_for_update.return_value.filter.return_value.exclude.assert_called_once_with(
            status='running')
        self.assertEqual(record.status, 'failed')
        self.assertTrue(record.source_detail['outcome_unknown'])
        self.assertEqual(record.error_message, 'response timeout')
        self.assertEqual(record.source_detail['outcome_resolution']['basis'], 'owned_resource_verified')
        saved.assert_called_once()

    def test_no_resource_proof_does_not_write_any_resolution(self):
        from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService as Audit
        with patch.object(Audit, 'save_completion') as saved:
            Audit.confirm_resource_requests([])
        saved.assert_not_called()

    def test_retry_checks_only_own_attempt_and_exact_original_requests(self):
        from django.db.models import Q
        from src.apps.data_factory.selectors.execution_audit import ExecutionAuditSelector
        manager = Mock()
        pending = manager.filter.return_value.filter.return_value
        with patch('src.apps.data_factory.selectors.execution_audit.SqlExecutionRecord.objects', manager):
            pending.exists.return_value = True
            self.assertFalse(ExecutionAuditSelector.case_operations_confirmed(7, 2, ['original-request']))
            pending.exists.return_value = False
            self.assertTrue(ExecutionAuditSelector.case_operations_confirmed(7, 2, ['original-request']))
        own = Q(source_detail__case_detail_id=7, source_detail__case_attempt=2) | Q(
            request_id__in=['original-request'])
        manager.filter.assert_called_with(own)
        manager.filter.return_value.filter.assert_called_with(Q(status='running') | Q(
            source_detail__outcome_unknown=True, source_detail__outcome_resolution__isnull=True))

    def test_unrelated_instance_occupancy_does_not_gate_safe_case_review(self):
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
        from src.apps.data_factory.selectors.execution_audit import ExecutionAuditSelector
        from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
        detail = SimpleNamespace(id=7, retry=2, summary_data={'meta': {'execution_control': {
            'issues': [{'request_id': 'original-request'}]}}})
        with patch.object(Infrastructure, 'cleanup_review_ready', return_value=True), \
                patch.object(ExecutionAuditSelector, 'case_operations_confirmed', return_value=True) as audit, \
                patch.object(Governor, 'store') as global_state:
            self.assertTrue(Infrastructure.review_ready(detail))
        audit.assert_called_once_with(7, 2, ['original-request'])
        global_state.assert_not_called()

    def test_incomplete_cleanup_still_blocks_review(self):
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
        from src.apps.data_factory.selectors.execution_audit import ExecutionAuditSelector
        with patch.object(Infrastructure, 'cleanup_review_ready', return_value=False), \
                patch.object(ExecutionAuditSelector, 'case_operations_confirmed') as audit:
            self.assertFalse(Infrastructure.review_ready(SimpleNamespace(id=7, retry=2)))
        audit.assert_not_called()
