import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import OperationalError
from django.test import SimpleTestCase

from src.apps.data_factory.enums.performance import DatasourcePermitKindEnum
from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.data_factory.services.datasource.datasource_connection import GovernedDbapiConnection
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.recovery.permit_reconciliation import DatasourcePermitReconciliationService as Recovery
from src.apps.data_factory.tests.test_datasource_performance import AtomicMemoryStore


class ConnectionClosureProofTests(SimpleTestCase):
    def setUp(self):
        self.store = AtomicMemoryStore()
        for guard in (patch.object(Governor, 'store', return_value=self.store),
                patch.object(Governor, 'policy', return_value=DatasourcePerformancePolicy()),
                patch.object(Governor, 'configuration_guard', side_effect=lambda *args: nullcontext()),
                patch.object(Governor, '_closed_connections', set()),
                patch.object(Governor, '_closed_pid', os.getpid())):
            guard.start()
            self.addCleanup(guard.stop)
        self.target = SimpleNamespace(id=49, db_type=0, host='mysql.example.com', port=3306)
        self.permit = Governor.acquire(self.target, wait=False)
        self.group, self.owner = self.permit

    def defer(self):
        update = self.store.atomic_update
        def fail_group(key, *args, **kwargs):
            if key.startswith('group:'):
                raise OperationalError(2013, 'control response lost')
            return update(key, *args, **kwargs)
        with patch.object(self.store, 'atomic_update', side_effect=fail_group):
            GovernedDbapiConnection(Mock(), self.permit).close()
        return f'closed:{self.group}:{self.owner}'

    def test_close_proof_survives_worker_restart_and_is_idempotent(self):
        key = self.defer()
        self.assertIn(key, self.store.values)
        Governor._closed_connections.clear()
        with patch.object(Governor, 'process_identity', return_value='replacement-worker:1'):
            self.assertEqual(Recovery.recover_closed_connections(self.group), 1)
            self.assertEqual(Recovery.recover_closed_connections(self.group), 0)
        self.assertNotIn(key, self.store.values)
        self.assertEqual(self.store.values[f'group:{self.group}:control']['completed'], 1)

    def test_actual_worker_process_exit_recovers_persisted_close_not_parent_memory(self):
        import json
        import subprocess
        import sys
        import time
        child = subprocess.run([sys.executable, '-m',
            'src.apps.data_factory.tests.permit_recovery_worker_fixture'],
            capture_output=True, text=True, timeout=30, check=True)
        line = next(value for value in child.stdout.splitlines() if value.startswith('PERMIT_RECOVERY_FIXTURE='))
        self.store.values = json.loads(line.split('=', 1)[1])['values']
        self.store.now = time.time() + 301
        Governor._closed_connections.clear()
        proof = next(value for key, value in self.store.values.items() if key.startswith('closed:'))
        self.assertNotEqual(proof['process'], Governor.process_identity())
        self.assertEqual(Recovery.recover_closed_connections(self.group), 1)
        self.assertFalse(self.store.values[f'group:{self.group}:control']['permits'])

    def test_proof_never_releases_changed_process_or_operation_owner(self):
        self.defer()
        state = self.store.values[f'group:{self.group}:control']
        state['permits'][self.owner]['process'] = 'different-process'
        self.assertEqual(Recovery.recover_closed_connections(self.group), 0)
        self.assertIn(self.owner, state['permits'])

    def test_future_or_pre_admission_proof_is_not_consumed(self):
        key = self.defer()
        for stamp in (self.store.now + 10, self.store.now - 10):
            self.store.values[key]['confirmed_at'] = stamp
            self.assertEqual(Recovery.recover_closed_connections(self.group), 0)

    def test_physical_close_failure_never_persists_close_proof(self):
        native = Mock(close=Mock(side_effect=OSError('socket close unknown')))
        with self.assertRaises(OSError):
            GovernedDbapiConnection(native, self.permit).close()
        self.assertFalse(any(key.startswith('closed:') for key in self.store.values))
        self.assertEqual(Recovery.recover_closed_connections(self.group), 0)

    def test_recovery_keeps_unrelated_connections_and_never_calls_business_database(self):
        self.defer()
        other = Governor.acquire(self.target, wait=False)
        self.assertEqual(Recovery.recover_closed_connections(self.group), 1)
        self.assertIn(other[1], self.store.values[f'group:{self.group}:control']['permits'])

    def test_hot_config_change_rechecks_admission_without_failing_or_replaying(self):
        from src.apps.data_factory.exceptions import DatasourcePolicyRefreshRequired
        refreshed = DatasourcePerformancePolicy()
        original = Governor.change
        calls = 0
        def change(group, callback, **kwargs):
            nonlocal calls
            if kwargs.get('expected_policy') is not None:
                calls += 1
                if calls == 1:
                    raise DatasourcePolicyRefreshRequired(refreshed)
                self.assertEqual(kwargs['expected_policy'], refreshed)
            return original(group, callback, **kwargs)
        with patch.object(Governor, 'change', side_effect=change):
            operation = Governor.acquire(self.target, wait=False)
        self.assertEqual(calls, 2)
        permits = self.store.values[f'group:{self.group}:control']['permits']
        self.assertEqual(set(permits), {self.owner, operation[1]})

    def test_concurrent_recovery_cannot_double_release_or_touch_unproven_owner(self):
        self.defer()
        keep = Governor.acquire(self.target, wait=False)
        with ThreadPoolExecutor(max_workers=16) as executor:
            settled = list(executor.map(lambda _: Recovery.recover_closed_connections(self.group), range(64)))
        self.assertEqual(sum(settled), 1)
        state = self.store.values[f'group:{self.group}:control']
        self.assertEqual(state['completed'], 1)
        self.assertEqual(set(state['permits']), {keep[1]})
