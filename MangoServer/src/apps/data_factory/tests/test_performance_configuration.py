import json
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone
from mangotools.enums import CacheValueTypeEnum

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy, DatasourceGovernorState, DatasourcePermit
from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService as Governor
from src.apps.system.services.system_config import SystemConfigService


class PerformanceConfigurationTests(SimpleTestCase):
    def test_relaxed_defaults_increase_throughput_and_waiting_capacity_without_weakening_cleanup(self):
        policy = DatasourcePerformancePolicy()
        for kind, expected in {'mysql': (6, 30, 12), 'redis': (12, 75, 16), 'elasticsearch': (6, 15, 12)}.items():
            budget = getattr(policy, kind)
            self.assertEqual((budget.concurrency, budget.requests_per_second, budget.connections), expected)
            self.assertEqual(budget.cleanup_reserved, 2)
            self.assertEqual(budget.cleanup_rate_percent, 25)
            self.assertEqual(budget.metadata_per_second, 2)
            self.assertEqual(budget.cleanup_backlog_limit, 100)
        self.assertEqual(policy.max_waiters, 256)
        self.assertEqual(policy.pool_size, 3)
        self.assertEqual(policy.cleanup_consumer_threads, 2)
        self.assertEqual(policy.queue_timeout_seconds, 30)
        self.assertEqual(policy.permit_lease_seconds, 300)
        self.assertEqual(policy.cleanup_completion_seconds, 300)

    def test_existing_explicit_values_and_valid_low_custom_budgets_are_preserved(self):
        value = {'mysql': {'concurrency': 4, 'requests_per_second': 20, 'connections': 8,
                           'cleanup_reserved': 1, 'metadata_per_second': 1}, 'pool_size': 2, 'max_waiters': 100}
        parsed = Governor.parse_saved_policy(value)
        self.assertEqual(parsed.mysql.concurrency, 4)
        self.assertEqual(parsed.mysql.connections, 8)
        self.assertEqual(parsed.mysql.cleanup_reserved, 1)
        self.assertEqual(parsed.pool_size, 2)
        self.assertEqual(parsed.max_waiters, 100)
        for kind in ('mysql', 'redis', 'elasticsearch'):
            low = {kind: {'concurrency': 2, 'connections': 3}}
            parsed = Governor.parse_saved_policy(low)
            self.assertEqual(getattr(parsed, kind).cleanup_reserved, 1)
            self.assertEqual(parsed.pool_size, 2)
            self.assertEqual(low, {kind: {'concurrency': 2, 'connections': 3}})

    def test_expanded_waiter_state_fits_the_registered_runtime_storage_budget(self):
        from src.apps.data_factory.schemas.performance import DatasourceWaiter
        from src.apps.system.constants import RUNTIME_KV_POLICIES
        maximum = DatasourcePerformancePolicy.model_json_schema()['properties']['max_waiters']['maximum']
        state = DatasourceGovernorState(
            permits={f'{i:032x}': DatasourcePermit(owner=f'{i:032x}', process='w' * 128,
                kind='connection' if i < 128 else 'operation', lane='normal', expires_at=1800000300.123456,
                case_detail_id=999999999999999999, case_attempt=100) for i in range(192)},
            waiters={f'{i:032x}': DatasourceWaiter(lane='normal', created_at=1800000000.123456,
                expires_at=1800000030.123456) for i in range(maximum)})
        encoded = json.dumps({'data': state.model_dump(mode='json'), 'schema_version': 1}).encode()
        self.assertLess(len(encoded) + 1024, RUNTIME_KV_POLICIES['datasource_governor']['max_bytes'])

    def test_uniform_type_budgets_are_identical_for_different_instances_but_counts_are_separate(self):
        policy = DatasourcePerformancePolicy()
        first = SimpleNamespace(id=1, db_type=0, host='first.example.com', port=3306)
        second = SimpleNamespace(id=2, db_type=0, host='second.example.com', port=3306)
        _, first_budget, first_group = Governor.target_policy(first, policy)
        _, second_budget, second_group = Governor.target_policy(second, policy)
        self.assertEqual(first_budget, second_budget)
        self.assertNotEqual(first_group, second_group)
        self.assertNotIn('instances', policy.model_dump())
        self.assertNotIn('scopes', policy.model_dump())

    def test_new_config_rejects_removed_override_and_scope_fields(self):
        from pydantic import ValidationError
        for key in ('instances', 'scopes'):
            with self.subTest(key=key), self.assertRaises(ValidationError):
                DatasourcePerformancePolicy.model_validate({key: []}, strict=True)

    def test_saved_empty_retired_options_do_not_block_existing_cases(self):
        self.assertEqual(Governor.parse_saved_policy({'instances': [], 'scopes': []}), DatasourcePerformancePolicy())

    def test_nonempty_retired_policy_is_not_silently_ignored(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            Governor.parse_saved_policy({'instances': [{'group': 'old'}]})

    def test_old_runtime_scope_metadata_does_not_remove_unknown_permits(self):
        old = DatasourceGovernorState(permits={'owner': DatasourcePermit(
            owner='owner', process='example', kind='operation', lane='normal', state='suspect', expires_at=10)}).model_dump(mode='json')
        old['scopes'] = {'old': {'tokens': 100}}
        old['permits']['owner']['scopes'] = ['old']
        state = Governor.read_state(old)
        self.assertEqual(state.permits['owner'].state.value, 'suspect')
        self.assertEqual(state.permits['owner'].expires_at, 10)
        self.assertIn('scopes', old)
        self.assertNotIn('scopes', state.model_dump())

    @patch('src.apps.system.selectors.runtime_kv.RuntimeKVSelector.active')
    @patch('src.apps.system.services.runtime_kv.store.RuntimeKVStore.server_time', side_effect=timezone.now)
    def test_retired_instance_override_cannot_bypass_inflight_unknown_ownership(self, clock, active):
        previous = SimpleNamespace(value=json.dumps({'instances': [{'group': 'old'}]}), value_type=CacheValueTypeEnum.DICT.value)
        state = DatasourceGovernorState(permits={'owner': DatasourcePermit(
            owner='owner', process='example', kind='operation', lane='normal', state='suspect', expires_at=10)})
        rows = active.return_value.filter.return_value.select_for_update.return_value.only
        rows.return_value = [SimpleNamespace(value={'data': state.model_dump(mode='json')})]
        self.assertIn('不能直接重置', SystemConfigService.validate_datasource_policy_transition(previous, {}))
        rows.return_value = []
        self.assertIsNone(SystemConfigService.validate_datasource_policy_transition(previous, {}))

    def test_invalid_saved_policy_is_visible_without_breaking_the_repair_page(self):
        from src.apps.data_factory.exceptions import DATASOURCE_POLICY_INVALID
        from src.apps.data_factory.services.datasource_performance import DatasourcePerformanceService
        with patch.object(DatasourcePerformanceService, 'settings_status', side_effect=DataFactoryError(DATASOURCE_POLICY_INVALID)):
            snapshot = DatasourcePerformanceService.settings_snapshot()
        self.assertEqual(snapshot['runtime_status'], [])
        self.assertIn('配置管理', snapshot['performance_notice'])

    def test_all_datasource_performance_fields_inherit_cautious_management_level(self):
        from src.apps.system.enums.cache import SystemConfigManagementLevelEnum
        from src.apps.system.services.system_config import SYSTEM_CONFIG_REGISTRY
        definition = next(item for item in SYSTEM_CONFIG_REGISTRY if item.key == 'DATASOURCE_PERFORMANCE_POLICY')
        self.assertEqual(definition.management_level, SystemConfigManagementLevelEnum.CAUTION.value)
        self.assertEqual(definition.default_value, {})

    def test_status_counts_reserved_physical_slots_not_pool_tokens(self):
        from src.apps.data_factory.services.datasource_performance import DatasourcePerformanceService
        target = SimpleNamespace(id=1, db_type=0, host='example.com', port=3306)
        policy = DatasourcePerformancePolicy()
        group = Governor.target_policy(target, policy)[2]
        state = DatasourceGovernorState()
        state.permits['pool'] = DatasourcePermit(owner='pool', process='test', lane='normal',
                                                kind='connection', slots=2, expires_at=1000)
        row = SimpleNamespace(key=f'group:{group}:control', value={'data': state.model_dump(mode='json')})
        with patch('src.apps.data_factory.services.datasource_performance.Database.objects') as databases, \
                patch('src.apps.system.selectors.runtime_kv.RuntimeKVSelector.entries', return_value=[row]), \
                patch.object(Governor, 'policy', return_value=policy), \
                patch.object(Governor, 'store') as store:
            databases.only.return_value.all.return_value = [target]
            store.return_value.server_time.return_value.timestamp.return_value = 500
            self.assertEqual(DatasourcePerformanceService.settings_status()[0]['counts']['connection_active'], 2)

    def test_cleanup_consumers_default_to_two_and_cannot_be_disabled(self):
        from pydantic import ValidationError
        self.assertEqual(DatasourcePerformancePolicy().cleanup_consumer_threads, 2)
        for value in (0, 17, 1.5, '2', True):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                DatasourcePerformancePolicy.model_validate({'cleanup_consumer_threads': value}, strict=True)
        self.assertEqual(DatasourcePerformancePolicy(cleanup_consumer_threads=16).cleanup_consumer_threads, 16)

    @patch('src.apps.system.selectors.configuration.ConfigurationSelector.shared_locked_value')
    @patch('src.apps.data_factory.services.datasource_governor.transaction.atomic', side_effect=lambda **kwargs: nullcontext())
    def test_scheduler_thread_change_does_not_invalidate_inflight_datasource_budget(self, atomic, locked):
        previous = DatasourcePerformancePolicy()
        current = previous.model_dump(mode='json')
        current['cleanup_consumer_threads'] = 3
        locked.return_value = (json.dumps(current), CacheValueTypeEnum.DICT.value)
        with Governor.configuration_guard('unit', previous):
            pass

    @patch('src.apps.system.selectors.configuration.ConfigurationSelector.shared_locked_value')
    @patch('src.apps.data_factory.services.datasource_governor.transaction.atomic', side_effect=lambda **kwargs: nullcontext())
    def test_stale_policy_cannot_claim_old_quota_but_can_release_existing_permit(self, atomic, locked):
        current = DatasourcePerformancePolicy()
        changed = current.model_dump(mode='json')
        changed['mysql']['requests_per_second'] = 21
        locked.return_value = (json.dumps(changed), CacheValueTypeEnum.DICT.value)
        with self.assertRaises(DataFactoryError) as error:
            with Governor.configuration_guard('unit', current):
                self.fail('stale policy must not run')
        self.assertEqual(error.exception.code, 34184)
        with Governor.configuration_guard('unit'):
            pass

    @patch('src.apps.system.selectors.runtime_kv.RuntimeKVSelector.active')
    @patch('src.apps.system.services.runtime_kv.store.RuntimeKVStore.server_time', side_effect=timezone.now)
    def test_identity_change_requires_drained_connections(self, server_time, active):
        previous = SimpleNamespace(value='{}', value_type=CacheValueTypeEnum.DICT.value)
        current = DatasourcePerformancePolicy().model_dump(mode='json')
        current['pool_size'] = 4
        state = DatasourceGovernorState()
        state.permits['one'] = DatasourcePermit(owner='one', process='test', lane='normal', kind='connection',
                                               expires_at=timezone.now().timestamp() + 60)
        rows = active.return_value.filter.return_value.select_for_update.return_value.only
        rows.return_value = [SimpleNamespace(value={'data': state.model_dump(mode='json')}, kv_now=timezone.now())]
        message = SystemConfigService.validate_datasource_policy_transition(previous, current)
        self.assertIn('等待现有清理完成、连接池回收', message)
        rows.return_value = []
        self.assertIsNone(SystemConfigService.validate_datasource_policy_transition(previous, current))

    @patch('src.apps.system.selectors.runtime_kv.RuntimeKVSelector.active')
    def test_limit_changes_keep_same_group_and_do_not_discard_permits(self, active):
        previous = SimpleNamespace(value='{}', value_type=CacheValueTypeEnum.DICT.value)
        current = DatasourcePerformancePolicy().model_dump(mode='json')
        current['mysql']['concurrency'] = 4
        self.assertIsNone(SystemConfigService.validate_datasource_policy_transition(previous, current))
        active.assert_not_called()
