"""配额控制事务锁冲突恢复；不访问共享数据库或重放业务操作。"""

import copy
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import InterfaceError, OperationalError
from django.test import SimpleTestCase

from src.apps.data_factory.enums.performance import DatasourceQueueLaneEnum
from src.apps.data_factory.exceptions import DataFactoryError, DATASOURCE_POLICY_INVALID
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.tests.test_datasource_performance import AtomicMemoryStore


class ControlLockRecoveryTests(SimpleTestCase):
    def setUp(self):
        self.store = AtomicMemoryStore()
        self.in_transaction = False
        self.guards = 0
        self.confirmed = 0
        self.pauses = 0
        self.store.confirm_control_rollback = Mock(side_effect=self.confirm_rollback)
        self.target = SimpleNamespace(id=1, db_type=0, host='mysql.example.com', port=3306)
        self.policy = DatasourcePerformancePolicy()
        for guard in (
            patch.object(Governor, 'store', return_value=self.store),
            patch.object(Governor, 'policy', return_value=self.policy),
            patch.object(Governor, 'lane', return_value=DatasourceQueueLaneEnum.NORMAL),
            patch.object(Governor, 'configuration_guard', side_effect=self.configuration_guard),
            patch.object(Governor, '_pending_releases', set()),
            patch('src.apps.data_factory.services.governance.datasource_wait.DatasourceWaitService.pause', side_effect=self.pause),
        ):
            guard.start()
            self.addCleanup(guard.stop)

    @contextmanager
    def configuration_guard(self, using, expected=None):
        self.assertFalse(self.in_transaction)
        self.guards += 1
        self.in_transaction = True
        before = copy.deepcopy(self.store.values)
        try:
            yield
        except BaseException:
            self.store.values = before
            raise
        finally:
            self.in_transaction = False

    def confirm_rollback(self):
        self.assertFalse(self.in_transaction)
        self.confirmed += 1

    def pause(self, seconds):
        self.assertFalse(self.in_transaction)
        self.assertGreaterEqual(self.confirmed, self.pauses + 1)
        self.pauses += 1

    def state(self):
        return next(iter(self.store.values.values()))

    def fail_after_update(self, code, count):
        update = self.store.atomic_update
        remaining = [count]
        def run(*args, **kwargs):
            result = update(*args, **kwargs)
            if remaining[0]:
                remaining[0] -= 1
                raise OperationalError(code, 'AUTO_LOCK_CONFLICT')
            return result
        return run

    def test_repeated_lock_conflicts_wait_then_charge_one_admission(self):
        for code in (1205, 1213):
            with self.subTest(code=code):
                self.store.values.clear()
                before_guards, before_pauses = self.guards, self.pauses
                with patch.object(self.store, 'atomic_update', side_effect=self.fail_after_update(code, 5)):
                    permit = Governor.acquire(self.target, wait=False)
                self.assertEqual(self.guards - before_guards, 6)
                self.assertEqual(self.pauses - before_pauses, 5)
                self.assertEqual(self.state()['admitted'], 1)
                self.assertEqual(list(self.state()['permits']), [permit[1]])
                Governor.release(permit)

    def test_release_retries_only_control_transaction_not_business_sql(self):
        business = Mock()
        permit = Governor.acquire(self.target)
        business()
        with patch.object(self.store, 'atomic_update', side_effect=self.fail_after_update(1205, 4)):
            Governor.connection_closed(permit)
        business.assert_called_once()
        self.assertEqual(self.state()['completed'], 1)
        self.assertFalse(self.state()['permits'])
        self.assertFalse(Governor._pending_releases)

    def test_unknown_commit_or_disconnect_is_not_retried(self):
        for error in (OperationalError(2013, 'AUTO_REPLY_LOST'), OperationalError(2006, 'AUTO_CLOSED'),
                      InterfaceError(0, 'AUTO_CLOSED')):
            with self.subTest(code=error.args[0]):
                with patch.object(self.store, 'atomic_update', side_effect=error) as update, \
                        self.assertRaises(DataFactoryError) as caught:
                    Governor.change('AUTO_GROUP', lambda state, now: True)
                self.assertEqual(caught.exception.code, 34185)
                self.assertIs(caught.exception.__cause__, error)
                update.assert_called_once()
        self.store.confirm_control_rollback.assert_not_called()
        self.assertEqual(self.pauses, 0)

    def test_failed_rollback_confirmation_never_retries(self):
        self.store.confirm_control_rollback.side_effect = OperationalError(2013, 'AUTO_ROLLBACK_UNKNOWN')
        with patch.object(self.store, 'atomic_update', side_effect=OperationalError(1205, 'AUTO_LOCK')) as update, \
                self.assertRaises(DataFactoryError):
            Governor.change('AUTO_GROUP', lambda state, now: True)
        update.assert_called_once()
        self.assertEqual(self.pauses, 0)

    def test_policy_is_rechecked_after_each_rollback(self):
        original = self.configuration_guard
        @contextmanager
        def changed_policy(*args):
            with original(*args):
                if self.guards == 2:
                    raise DataFactoryError(DATASOURCE_POLICY_INVALID)
                yield
        with patch.object(Governor, 'configuration_guard', side_effect=changed_policy), \
                patch.object(self.store, 'atomic_update', side_effect=self.fail_after_update(1205, 1)) as update, \
                self.assertRaises(DataFactoryError) as caught:
            Governor.change('AUTO_GROUP', lambda state, now: True, expected_policy=self.policy)
        self.assertEqual(caught.exception.code, DATASOURCE_POLICY_INVALID.code)
        update.assert_called_once()
        self.assertFalse(self.store.values)

    def test_stop_interrupts_lock_wait_with_no_committed_admission(self):
        with patch.object(self.store, 'atomic_update', side_effect=self.fail_after_update(1205, 1)), \
                patch('src.apps.data_factory.services.governance.datasource_wait.DatasourceWaitService.pause',
                      side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            Governor.change('AUTO_GROUP', lambda state, now: True)
        self.assertFalse(self.store.values)

    def test_concurrent_lock_recovery_preserves_shared_capacity_and_single_business_calls(self):
        local = threading.local()
        barrier = threading.Barrier(4)
        business_calls = []
        update = self.store.atomic_update
        def conflict_once(*args, **kwargs):
            if not getattr(local, 'conflicted', False):
                local.conflicted = True
                raise OperationalError(1205, 'AUTO_CONCURRENT_LOCK')
            return update(*args, **kwargs)
        def execute(number):
            permit = Governor.acquire(self.target)
            try:
                business_calls.append(number)
                barrier.wait(timeout=5)
            finally:
                Governor.connection_closed(permit)
        with patch.object(Governor, 'configuration_guard', side_effect=lambda *args: nullcontext()), \
                patch.object(self.store, 'atomic_update', side_effect=conflict_once), \
                patch.object(self.store, 'confirm_control_rollback') as confirm, \
                patch('src.apps.data_factory.services.governance.datasource_wait.DatasourceWaitService.pause'), \
                ThreadPoolExecutor(max_workers=4) as workers:
            list(workers.map(execute, range(4)))
        self.assertEqual(sorted(business_calls), list(range(4)))
        self.assertEqual(confirm.call_count, 4)
        self.assertEqual(self.state()['admitted'], 4)
        self.assertEqual(self.state()['completed'], 4)
        self.assertFalse(self.state()['permits'])
