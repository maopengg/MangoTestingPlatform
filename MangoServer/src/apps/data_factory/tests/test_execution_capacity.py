from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.data_factory.enums.performance import DatasourceQueueLaneEnum
from src.apps.data_factory.exceptions import DataFactoryError, DATASOURCE_GOVERNOR_UNAVAILABLE
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.execution_capacity import DatasourceExecutionCapacityService as Capacity
from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService as Infrastructure
from src.apps.data_factory.services.datasource_wait import DatasourceAdmissionProbeService as Probe
from src.apps.data_factory.tests.test_datasource_performance import AtomicMemoryStore


class ExecutionCapacityTests(SimpleTestCase):
    def setUp(self):
        self.policy = DatasourcePerformancePolicy()
        self.target = SimpleNamespace(id=1, db_type=0, host='mysql.example.com', port=3306)
        self.store = AtomicMemoryStore()
        for method, value in [('store', self.store), ('policy', self.policy), ('lane', DatasourceQueueLaneEnum.NORMAL)]:
            guard = patch.object(Governor, method, return_value=value)
            guard.start()
            self.addCleanup(guard.stop)
        for guard in [patch.object(Governor, 'configuration_guard', side_effect=lambda *args: nullcontext()),
                      patch.object(Governor, '_pending_releases', set()), patch.object(Probe, '_due', {})]:
            guard.start()
            self.addCleanup(guard.stop)

    def test_one_product_with_multiple_aliases_counts_same_instance_once(self):
        bindings = [SimpleNamespace(database=self.target, environment=0,
                                    datasource_alias=SimpleNamespace(project_product_id=product)) for product in [1, 1, 2]]
        with patch('src.apps.data_factory.selectors.querysets.DataFactoryQuerySelector.execution_targets', return_value=bindings):
            targets = Capacity.targets_by_scope({(1, 0), (2, 0)}, self.policy)
        self.assertEqual(len(targets[(1, 0)]), 1)
        self.assertEqual(set(targets[(1, 0)]), set(targets[(2, 0)]))

    def test_infrastructure_scope_isolated_and_fixed_messages_exclude_driver_secrets(self):
        with Infrastructure.scope():
            with patch.object(self.store, 'atomic_update', side_effect=OSError('password must not escape')):
                with self.assertRaises(DataFactoryError):
                    Governor.acquire(self.target)
            self.assertEqual([issue.code for issue in Infrastructure.current()], [DATASOURCE_GOVERNOR_UNAVAILABLE.code])
            self.assertNotIn('password', Infrastructure.current()[0].message)
        self.assertFalse(Infrastructure.current())

    def test_unbound_product_does_not_create_synthetic_mysql_quota(self):
        with patch('src.apps.data_factory.selectors.querysets.DataFactoryQuerySelector.execution_targets', return_value=[]):
            self.assertEqual(Capacity.targets_by_scope({(1, 0)}, self.policy), {(1, 0): {}})

    def test_local_probe_only_oldest_registered_owner_coordinates_and_release_wakes_it(self):
        key = ('group', 'operation')
        Probe.congested(key, 'second', 2)
        Probe.congested(key, 'first', 1)
        Probe.changed('group')
        self.assertEqual(Probe.delay(key, 'first'), 0)
        self.assertGreater(Probe.delay(key, 'second'), 0)
        Probe.finished(key, 'first')
        self.assertEqual(Probe.delay(key, 'second'), 0)
        Probe.finished(key, 'second')
        self.assertFalse(Probe._due)

    def test_sql_unknown_result_still_retains_case_ownership_and_never_replays(self):
        from src.apps.data_factory.services.cleanup_schedule import DataFactoryCleanupScheduleService
        token = DataFactoryCleanupScheduleService.set_owner(17, 2)
        sent = Mock(side_effect=TimeoutError('AUTO unknown SQL result'))
        try:
            with self.assertRaises(TimeoutError):
                with Governor._operation(self.target, physical=True):
                    sent()
        finally:
            DataFactoryCleanupScheduleService.reset_owner(token)
        sent.assert_called_once()
        permit = next(iter(next(iter(self.store.values.values()))['permits'].values()))
        self.assertEqual((permit['case_detail_id'], permit['case_attempt'], permit['state']), (17, 2, 'suspect'))
