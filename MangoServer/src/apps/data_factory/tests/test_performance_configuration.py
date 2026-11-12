import json
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from mangotools.enums import CacheValueTypeEnum
from pydantic import ValidationError

from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.recovery.limit_retirement import DatasourceLimitRetirementService as Retirement
from src.apps.system.services.configuration.system_config import SystemConfigService


class PerformanceConfigurationTests(SimpleTestCase):
    def test_only_connection_and_cleanup_controls_remain(self):
        value = DatasourcePerformancePolicy().model_dump(mode='json')
        self.assertEqual(value, {'version': 2, 'mysql': {'connections': 20}, 'redis': {'connections': 16},
            'elasticsearch': {'connections': 12}, 'pool_size': 4, 'pool_idle_seconds': 60,
            'max_local_pools': 32, 'cleanup_completion_seconds': 300, 'cleanup_consumer_threads': 2})

    def test_retired_limits_are_rejected_not_silently_saved(self):
        for key in ('queue_timeout_seconds', 'max_waiters', 'permit_lease_seconds', 'transaction_statement_budget'):
            with self.subTest(key=key), self.assertRaises(ValidationError):
                DatasourcePerformancePolicy.model_validate({key: 100}, strict=True)
        for key in ('concurrency', 'requests_per_second', 'cleanup_reserved', 'cleanup_rate_percent',
                    'metadata_per_second', 'cleanup_backlog_limit'):
            with self.subTest(key=key), self.assertRaises(ValidationError):
                DatasourcePerformancePolicy.model_validate({'mysql': {key: 10}}, strict=True)

    def test_empty_type_objects_use_the_same_defaults_as_missing_types(self):
        expected = DatasourcePerformancePolicy().model_dump(mode='json')
        for kind in ('mysql', 'redis', 'elasticsearch'):
            for version in ({}, {'version': 2}):
                value = {**version, kind: {}}
                with self.subTest(value=value):
                    self.assertEqual(Governor.parse_saved_policy(value).model_dump(mode='json'), expected)
                    self.assertIsNone(SystemConfigService.validate_editable_config(
                        'DATASOURCE_PERFORMANCE_POLICY', json.dumps(value)))
                    self.assertEqual(value[kind], {})
        self.assertEqual(DatasourcePerformancePolicy.model_validate(
            {kind: {} for kind in ('mysql', 'redis', 'elasticsearch')}, strict=True).model_dump(mode='json'), expected)

    def test_explicit_type_values_are_not_overwritten_and_invalid_values_still_fail(self):
        for kind in ('mysql', 'redis', 'elasticsearch'):
            value = {kind: {'connections': 9}}
            with self.subTest(kind=kind):
                self.assertEqual(getattr(Governor.parse_saved_policy(value), kind).connections, 9)
                self.assertEqual(value[kind]['connections'], 9)
            for invalid in (None, [], '', {'connections': None}, {'connections': True},
                            {'connections': '20'}, {'connections': 0}, {'connections': 4},
                            {'concurrency': 10}):
                with self.subTest(kind=kind, invalid=invalid), self.assertRaises(ValidationError):
                    Governor.parse_saved_policy({kind: invalid})

    def test_retirement_normalizes_partial_v2_without_raising_saved_connection_values(self):
        value = {'version': 2, 'mysql': {}, 'redis': {}, 'elasticsearch': {}}
        self.assertEqual(Retirement.policy(value).model_dump(mode='json'),
                         DatasourcePerformancePolicy().model_dump(mode='json'))
        for version in (1, 2):
            with self.subTest(version=version):
                saved = Retirement.policy({'version': version, 'mysql': {'connections': 9}})
                self.assertEqual(saved.mysql.connections, 9)

    def test_strict_cleanup_and_reserved_connections_cannot_be_disabled(self):
        for value in ({'cleanup_consumer_threads': 0}, {'cleanup_completion_seconds': 0},
                      {'mysql': {'connections': 4}, 'pool_size': 4}):
            with self.assertRaises(ValidationError):
                DatasourcePerformancePolicy.model_validate(value, strict=True)

    def test_retirement_preserves_connection_choices_but_deletes_operation_controls(self):
        old = {'version': 1, 'mysql': {'connections': 12, 'concurrency': 6, 'requests_per_second': 30},
               'pool_size': 2, 'max_waiters': 100, 'permit_lease_seconds': 300}
        result = Retirement.policy(old).model_dump(mode='json')
        self.assertEqual(result['mysql'], {'connections': 12})
        self.assertEqual(result['pool_size'], 2)
        self.assertNotIn('max_waiters', result)
        self.assertNotIn('permit_lease_seconds', result)

    def test_retirement_never_drops_unknown_owner_audit_or_time_evidence(self):
        permit = {'owner': 'a'*32, 'process': 'old-worker', 'lane': 'normal', 'kind': 'operation',
                  'state': 'suspect', 'expires_at': 100, 'audit_record_id': 7, 'created_at': 90,
                  'case_detail_id': None, 'case_attempt': None}
        old = {'version': 1, 'tokens': 3, 'normal_tokens': 2, 'updated_at': 100, 'metadata_tokens': 1,
               'waiters': {}, 'permits': {'a'*32: permit}}
        result = Retirement.state(old)
        self.assertEqual(result['permits']['a'*32], {**permit, 'slots': 1})
        self.assertEqual(result['version'], 2)
        self.assertNotIn('tokens', result)
        self.assertNotIn('waiters', result)

    @patch('src.apps.system.selectors.configuration.ConfigurationSelector.shared_locked_value')
    @patch('src.apps.data_factory.services.governance.datasource_governor.transaction.atomic', side_effect=lambda **kwargs: nullcontext())
    def test_cleanup_thread_changes_do_not_invalidate_connection_admission(self, atomic, locked):
        current = DatasourcePerformancePolicy()
        changed = current.model_dump(mode='json')
        changed['cleanup_consumer_threads'] = 3
        locked.return_value = (json.dumps(changed), CacheValueTypeEnum.DICT.value)
        with Governor.configuration_guard('unit', current):
            pass

    def test_budget_changes_do_not_change_instance_identity(self):
        one = SimpleNamespace(id=1, db_type=0, host='mysql.example.com', port=3306)
        two = SimpleNamespace(id=2, db_type=0, host='mysql.example.com', port=3306)
        self.assertEqual(Governor.target_policy(one, DatasourcePerformancePolicy())[2],
                         Governor.target_policy(two, DatasourcePerformancePolicy(mysql={'connections': 30}))[2])

    def test_runtime_does_not_run_legacy_policy_as_a_parallel_implementation(self):
        with self.assertRaises(ValidationError):
            Governor.parse_saved_policy({'version': 1, 'mysql': {'concurrency': 4}})

    def test_unused_connection_configuration_has_complete_zero_runtime_shape(self):
        from src.apps.data_factory.services.governance.datasource_performance import DatasourcePerformanceService
        target = SimpleNamespace(id=1, db_type=0, host='mysql.example.com', port=3306)
        with patch('src.apps.data_factory.services.governance.datasource_performance.Database.objects') as databases, \
                patch.object(Governor, 'policy', return_value=DatasourcePerformancePolicy()), \
                patch('src.apps.data_factory.services.governance.datasource_performance.RuntimeKVSelector.entries', return_value=[]), \
                patch.object(Governor, 'store') as store:
            databases.only.return_value.all.return_value = [target]
            store.return_value.server_time.return_value.timestamp.return_value = 1
            row = DatasourcePerformanceService.settings_status()[0]
        self.assertFalse(row['connection_waiting'])
        self.assertEqual(row['counts'], {})
        self.assertEqual(row['completed'], 0)

    def test_pool_resize_checks_connections_but_not_retired_operation_evidence(self):
        previous = SimpleNamespace(value=json.dumps(DatasourcePerformancePolicy().model_dump(mode='json')),
                                   value_type=CacheValueTypeEnum.DICT.value)
        updated = DatasourcePerformancePolicy(pool_size=2).model_dump(mode='json')
        permit = {'owner': 'a'*32, 'process': 'old-worker', 'lane': 'normal', 'kind': 'operation',
                  'state': 'suspect', 'expires_at': 1}
        row = SimpleNamespace(value={'data': {'version': 2, 'permits': {'a'*32: permit}}})
        queryset = SimpleNamespace(filter=lambda **kw: SimpleNamespace(select_for_update=lambda:
            SimpleNamespace(only=lambda *args: [row])))
        with patch('src.apps.system.selectors.runtime_kv.RuntimeKVSelector.active', return_value=queryset), \
                patch('src.apps.system.services.runtime_kv.RuntimeKV.namespace') as store:
            store.return_value.server_time.return_value.timestamp.return_value = 1000
            self.assertIsNone(SystemConfigService.validate_datasource_policy_transition(previous, updated))
            permit['kind'] = 'connection'
            self.assertIsNotNone(SystemConfigService.validate_datasource_policy_transition(previous, updated))
