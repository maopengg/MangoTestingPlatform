"""有界故障注入：不连接共享业务库，不以时钟推进代替真实长稳压测。"""
import json
import os
import subprocess
import sys
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch
from unittest import skipUnless
from uuid import UUID

from django.db import InterfaceError, OperationalError
from django.test import SimpleTestCase

from src.apps.data_factory.enums.performance import DatasourcePermitKindEnum, DatasourceQueueLaneEnum
from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.data_factory.services.datasource_connection import GovernedDbapiConnection
from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.pool_maintenance import DatasourcePoolMaintenance as Maintenance
from src.apps.data_factory.services.type_cast import DataFactoryTypeCast
from src.apps.data_factory.tests.test_datasource_performance import AtomicMemoryStore
from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum
from src.apps.system.services.runtime_kv import RuntimeKV


class ControlConnectionRecoveryTests(SimpleTestCase):
    def setUp(self):
        self.store = RuntimeKV.namespace(RuntimeKVNamespaceEnum.DATASOURCE_GOVERNOR)
        self.store.using = 'runtime_kv_control'
        self.connection = Mock(in_atomic_block=False, errors_occurred=True)
        self.guard = patch('src.apps.system.services.runtime_kv.store.connections',
                           {'runtime_kv_control': self.connection})
        self.guard.start()
        self.addCleanup(self.guard.stop)
        probe = patch.object(self.store, 'control_connection_usable', return_value=True)
        self.probe = probe.start()
        self.addCleanup(probe.stop)

    def test_idle_disconnected_connection_is_rebuilt_before_callback(self):
        self.probe.return_value = False
        with self.store.control_connection():
            self.connection.close.assert_called_once()
            self.connection.ensure_connection.assert_called_once()

    def test_reconnection_debug_event_is_transition_only_and_has_no_connection_details(self):
        self.probe.return_value = False
        self.connection.password = 'test-only-secret'
        with self.assertLogs('system', level='DEBUG') as captured:
            with self.store.control_connection():
                pass
        self.assertEqual(len(captured.output), 1)
        self.assertIn('event=datasource_control_reconnected', captured.output[0])
        self.assertIn('namespace=datasource_governor', captured.output[0])
        self.assertNotIn('test-only-secret', captured.output[0])
        self.probe.return_value = True
        with self.assertNoLogs('system', level='DEBUG'):
            with self.store.control_connection():
                pass

    def test_failed_reconnect_never_logs_a_success_event(self):
        self.probe.return_value = False
        self.connection.ensure_connection.side_effect = OperationalError(2013, 'lost')
        with self.assertNoLogs('system', level='DEBUG'), self.assertRaises(OperationalError):
            with self.store.control_connection():
                self.fail('must not execute callback')

    def test_mid_transaction_disconnect_is_not_replayed_and_next_call_recovers(self):
        callback = Mock(side_effect=InterfaceError(0, 'disconnected'))
        with self.assertRaises(InterfaceError):
            with self.store.control_connection():
                callback()
        callback.assert_called_once()
        self.connection.close.assert_called_once()
        with self.store.control_connection():
            pass
        self.assertEqual(self.connection.ensure_connection.call_count, 2)

    def test_control_close_failure_does_not_replace_original_transaction_error(self):
        original = OperationalError(2013, 'original transaction failure')
        self.connection.close.side_effect = InterfaceError(0, 'already closed')
        with self.assertRaises(OperationalError) as caught:
            with self.store.control_connection():
                raise original
        self.assertIs(caught.exception, original)

    def test_healthy_connection_is_reused_and_outer_transaction_cannot_be_reconnected(self):
        with self.store.control_connection():
            pass
        self.connection.close.assert_not_called()
        self.connection.in_atomic_block = True
        from django.core.exceptions import ImproperlyConfigured
        with self.assertRaises(ImproperlyConfigured):
            with self.store.control_connection():
                self.fail('must not enter existing transaction')
        self.connection.close.assert_not_called()

    def test_probe_never_uses_driver_ping_autoreconnect(self):
        from src.apps.system.services.runtime_kv.store import RuntimeKVStore
        connection = MagicMock()
        cursor = connection.connection.cursor.return_value.__enter__.return_value
        self.assertTrue(RuntimeKVStore.control_connection_usable(connection))
        cursor.execute.assert_called_once_with('SELECT 1')
        connection.connection.ping.assert_not_called()
        cursor.execute.side_effect = InterfaceError(0, 'closed')
        self.assertFalse(RuntimeKVStore.control_connection_usable(connection))

    def test_confirm_control_rollback_requires_old_session_acknowledgement(self):
        self.connection.closed_in_transaction = False
        self.store.confirm_control_rollback()
        self.connection.rollback.assert_called_once()
        self.connection.ensure_connection.assert_not_called()
        self.connection.rollback.side_effect = OperationalError(2013, 'AUTO_ROLLBACK_REPLY_LOST')
        with self.assertRaises(OperationalError):
            self.store.confirm_control_rollback()
        self.connection.ensure_connection.assert_not_called()

    def test_unusable_or_nested_control_session_cannot_confirm_rollback(self):
        from django.core.exceptions import ImproperlyConfigured
        self.connection.closed_in_transaction = False
        for field, value in (('in_atomic_block', True), ('connection', None), ('closed_in_transaction', True)):
            with self.subTest(field=field), patch.object(self.connection, field, value), \
                    self.assertRaises(ImproperlyConfigured):
                self.store.confirm_control_rollback()
        self.connection.rollback.assert_not_called()
        self.connection.ensure_connection.assert_not_called()


class DatasourceRecoveryTests(SimpleTestCase):
    def setUp(self):
        self.store = AtomicMemoryStore()
        self.target = SimpleNamespace(id=1, db_type=0, host='mysql.example.com', port=3306)
        patches = [patch.object(Governor, 'store', return_value=self.store),
                   patch.object(Governor, 'policy', return_value=DatasourcePerformancePolicy()),
                   patch.object(Governor, 'lane', return_value=DatasourceQueueLaneEnum.NORMAL),
                   patch.object(Governor, 'configuration_guard', side_effect=lambda *args: nullcontext()),
                   patch.object(Governor, '_closed_connections', set()),
                   patch.object(Governor, '_pending_releases', set()),
                   patch.object(Governor, '_closed_pid', os.getpid())]
        for guard in patches:
            guard.start()
            self.addCleanup(guard.stop)

    def state(self):
        return next(iter(self.store.values.values()))

    def test_admission_commit_response_loss_cancels_only_never_started_owner(self):
        update = self.store.atomic_update
        calls = 0
        def lose_first_reply(*args, **kwargs):
            nonlocal calls
            result = update(*args, **kwargs)
            calls += 1
            if calls == 1:
                raise OperationalError(2013, 'commit reply lost')
            return result
        with patch.object(self.store, 'atomic_update', side_effect=lose_first_reply):
            with self.assertRaises(DataFactoryError) as caught:
                Governor.acquire(self.target, wait=False)
        self.assertTrue(caught.exception._datasource_not_sent)
        self.assertFalse(self.state()['permits'])
        self.assertFalse(Governor._pending_releases)

    def test_never_started_commit_uncertainty_is_reconciled_before_next_admission(self):
        update = self.store.atomic_update
        first = True
        def commit_then_disconnect(*args, **kwargs):
            nonlocal first
            if first:
                first = False
                update(*args, **kwargs)
            raise OperationalError(2013, 'control unavailable')
        with patch.object(self.store, 'atomic_update', side_effect=commit_then_disconnect):
            with self.assertRaises(DataFactoryError):
                Governor.acquire(self.target, wait=False)
        self.assertEqual(len(self.state()['permits']), 1)
        self.assertEqual(len(Governor._pending_releases), 1)
        fresh = Governor.acquire(self.target, wait=False)
        self.assertEqual(list(self.state()['permits']), [fresh[1]])
        self.assertFalse(Governor._pending_releases)
        Governor.release(fresh)

    def test_control_outage_before_claim_does_not_accumulate_fake_release_proofs(self):
        with patch.object(self.store, 'atomic_update', side_effect=OperationalError(2013, 'control unavailable')):
            for _ in range(20):
                with self.assertRaises(DataFactoryError):
                    Governor.acquire(self.target, wait=False)
        self.assertFalse(self.store.values)
        self.assertFalse(Governor._pending_releases)

    def test_completed_operation_release_failure_keeps_proof_without_replaying_business(self):
        business = Mock()
        operation = Governor.operation(self.target, physical=True)
        operation.__enter__()
        business()
        with patch.object(self.store, 'atomic_update', side_effect=OperationalError(2013, 'control unavailable')):
            with self.assertRaises(DataFactoryError) as caught:
                operation.__exit__(None, None, None)
        self.assertEqual(caught.exception.code, 34192)
        self.assertEqual(len(Governor._pending_releases), 1)
        Governor.flush_pending_releases()
        self.assertFalse(self.state()['permits'])
        business.assert_called_once()

    def test_release_commit_response_loss_is_idempotent_and_keeps_other_owners(self):
        keep = Governor.acquire(self.target, wait=False)
        done = Governor.acquire(self.target, wait=False)
        update = self.store.atomic_update
        def committed_then_lost(*args, **kwargs):
            update(*args, **kwargs)
            raise OperationalError(2013, 'release reply lost')
        with patch.object(self.store, 'atomic_update', side_effect=committed_then_lost):
            with self.assertRaises(DataFactoryError):
                Governor.release(done)
        completed = self.state()['completed']
        Governor.flush_pending_releases()
        self.assertEqual(self.state()['completed'], completed)
        self.assertEqual(list(self.state()['permits']), [keep[1]])
        self.assertFalse(Governor._pending_releases)

    def test_failed_business_preserves_original_error_and_unknown_remains_isolated(self):
        for error, unknown in ((RuntimeError('business failure'), False), (TimeoutError('unknown write'), True)):
            with self.subTest(unknown=unknown):
                operation = Governor.operation(self.target, physical=True)
                operation.__enter__()
                before = set(self.state()['permits'])
                with patch.object(self.store, 'atomic_update', side_effect=OperationalError(2013, 'control unavailable')):
                    self.assertFalse(operation.__exit__(type(error), error, None))
                self.assertTrue(error._datasource_settlement_failed)
                Governor.flush_pending_releases()
                if unknown:
                    self.assertEqual(set(self.state()['permits']), before)
                else:
                    self.assertFalse(self.state()['permits'])

    def test_existing_unknown_es_owner_can_be_settled_only_after_explicit_release(self):
        permit = Governor.acquire(self.target, wait=False)
        Governor.release(permit, unknown=True)
        self.state()['permits'][permit[1]]['process'] = 'previous-consumer:1'
        Governor.flush_pending_releases()
        self.assertIn(permit[1], self.state()['permits'])
        # 模拟已有 ES 快照回查确认后显式 release；不能靠进程变更或过期自动放行。
        with patch.object(self.store, 'atomic_update', side_effect=OperationalError(2013, 'control unavailable')):
            with self.assertRaises(DataFactoryError):
                Governor.release(permit)
        Governor.flush_pending_releases()
        self.assertFalse(self.state()['permits'])

    def test_cancelled_operation_stays_unknown_instead_of_freeing_capacity(self):
        operation = Governor.operation(self.target, physical=True)
        operation.__enter__()
        interrupt = KeyboardInterrupt()
        self.assertFalse(operation.__exit__(KeyboardInterrupt, interrupt, None))
        self.assertTrue(all(item['state'] == 'suspect' for item in self.state()['permits'].values()))
        Governor.flush_pending_releases()
        self.assertEqual(len(self.state()['permits']), 1)

    def test_protocol_factory_failure_keeps_every_reservation_for_reconciliation(self):
        from src.apps.data_factory.services.protocol_pool import ProtocolPoolRegistry as Pools
        self.target.update_time, self.target.user, self.target.extra_config = 'v1', 'tester', {}
        unavailable = patch.object(self.store, 'atomic_update', side_effect=OperationalError(2013, 'control unavailable'))
        original = RuntimeError('client construction failed')
        def factory(size):
            unavailable.start()
            raise original
        try:
            with patch.object(Pools, '_entries', {}), patch.object(Pools, '_pid', os.getpid()):
                with self.assertRaises(RuntimeError) as caught:
                    with Pools.borrow(self.target, 'redis', factory):
                        self.fail('client must not be returned')
            self.assertIs(caught.exception, original)
            self.assertEqual(len(Governor._pending_releases), 1)
            self.assertEqual(sum(item['slots'] for item in self.state()['permits'].values()), Governor.policy().pool_size)
        finally:
            unavailable.stop()
        # 维护线程尚未启动；下一次准入仍会先核销未使用的旧预留。
        fresh = Governor.acquire(self.target, wait=False)
        self.assertEqual(list(self.state()['permits']), [fresh[1]])
        Governor.release(fresh)

    def test_pending_operation_proofs_are_not_reused_in_fork_child(self):
        Governor._pending_releases.add(('parent-group', 'parent-owner'))
        with patch('src.apps.data_factory.services.datasource_governor.os.getpid', return_value=-1):
            Governor.flush_pending_releases()
        self.assertFalse(Governor._pending_releases)
        self.assertFalse(self.store.values)

    def test_24_hour_logical_soak_repeated_disconnect_close_recovery_and_no_quota_leak(self):
        writes = 0
        for tick in range(2880):
            permit = Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)
            physical = Mock()
            connection = GovernedDbapiConnection(physical, permit)
            operation = Governor.acquire(self.target, wait=False)
            writes += 1
            Governor.release(operation)
            if tick % 240 == 0:
                with patch.object(self.store, 'atomic_update', side_effect=OperationalError(2013, 'lost')):
                    with self.assertRaises(DataFactoryError):
                        connection.close()
                self.assertIn(permit, Governor._closed_connections)
                self.store.now += 600
                # 物理关闭已证明，控制面恢复后仅核销 owner，不执行 SQL 或再次物理 close。
                Governor.flush_closed_connections()
                connection.close()
            else:
                connection.close()
            physical.close.assert_called_once()
            self.assertFalse(Governor._closed_connections)
            self.assertFalse(self.state()['permits'])
            self.store.now += 30
        self.assertEqual(writes, 2880)

    def test_confirmation_after_control_commit_response_loss_is_idempotent(self):
        permit = Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)
        update = self.store.atomic_update
        def committed_then_lost(*args, **kwargs):
            update(*args, **kwargs)
            raise OperationalError(2013, 'lost commit response')
        with patch.object(self.store, 'atomic_update', side_effect=committed_then_lost):
            with self.assertRaises(DataFactoryError):
                Governor.connections_closed([permit])
        completed = self.state()['completed']
        Governor.flush_closed_connections()
        self.assertEqual(self.state()['completed'], completed)
        self.assertFalse(Governor._closed_connections)

    def test_failed_physical_close_keeps_suspect_and_cannot_use_close_confirmation(self):
        permit = Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)
        connection = GovernedDbapiConnection(Mock(close=Mock(side_effect=OSError('unknown close'))), permit)
        with self.assertRaises(OSError):
            connection.close()
        self.assertEqual(self.state()['permits'][permit[1]]['state'], 'suspect')
        self.assertFalse(Governor._closed_connections)
        self.store.now += 86400
        Governor.flush_closed_connections()
        self.assertIn(permit[1], self.state()['permits'])

    def test_all_pool_close_proofs_survive_control_failure(self):
        permits = [Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)
                   for _ in range(2)]
        with patch.object(self.store, 'atomic_update', side_effect=OperationalError(2013, 'lost')):
            with self.assertRaises(DataFactoryError):
                Governor.connections_closed(permits)
        self.assertEqual(Governor._closed_connections, set(permits))
        Governor.flush_closed_connections()
        self.assertFalse(self.state()['permits'])

    def test_release_debug_logs_only_deferred_and_recovery_counts_without_owner(self):
        permit = Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)
        with self.assertNoLogs('system', level='DEBUG'):
            Governor.connections_closed([permit])
            Governor.flush_closed_connections()
        permit = Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)
        with self.assertLogs('system', level='DEBUG') as captured:
            with patch.object(self.store, 'atomic_update', side_effect=OperationalError(2013, 'test-only-secret')):
                with self.assertRaises(DataFactoryError):
                    Governor.connections_closed([permit])
            Governor.flush_closed_connections()
        self.assertEqual(len(captured.output), 2)
        self.assertIn('event=datasource_connection_release_deferred pending_count=1', captured.output[0])
        self.assertIn('confirmed_count=1 pending_count=0', captured.output[1])
        for entry in captured.output:
            self.assertNotIn(permit[1], entry)
            self.assertNotIn('test-only-secret', entry)

    def test_admission_failure_not_masked_by_waiter_cleanup_and_no_callback_replay(self):
        with patch.object(self.store, 'atomic_update', side_effect=OperationalError(2013, 'lost')):
            with self.assertRaises(DataFactoryError) as caught:
                Governor.acquire(self.target, wait=False)
        self.assertEqual(caught.exception.code, 34185)
        self.assertTrue(caught.exception._datasource_not_sent)
        self.assertFalse(self.store.values)

    def test_fork_does_not_confirm_parent_connections_and_operations_cannot_be_released_as_closed(self):
        Governor._closed_connections.add(('parent', 'owner'))
        with patch('src.apps.data_factory.services.datasource_governor.os.getpid', return_value=-1):
            Governor.flush_closed_connections()
        self.assertFalse(Governor._closed_connections)
        operation = Governor.acquire(self.target, wait=False)
        with self.assertRaises(DataFactoryError):
            Governor.connections_closed([operation])
        self.assertIn(operation[1], self.state()['permits'])

    def test_close_proof_cannot_release_another_process_owner(self):
        permit = Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)
        self.state()['permits'][permit[1]]['process'] = 'other-process:1'
        with self.assertRaises(DataFactoryError):
            Governor.connections_closed([permit])
        self.assertIn(permit[1], self.state()['permits'])


class PoolMaintenanceTests(SimpleTestCase):
    def test_configuration_connection_failure_does_not_kill_maintenance_loop(self):
        with patch.object(Maintenance, '_states', {}), patch.object(Maintenance, '_pid', os.getpid()), \
                patch('src.common.logging.log.system'), \
                patch('django.db.close_old_connections', side_effect=[InterfaceError(0, 'closed'), None]):
            callback = Mock()
            self.assertFalse(Maintenance.run('sql', callback))
            callback.assert_not_called()
            self.assertTrue(Maintenance.run('sql', callback))
            callback.assert_called_once()

    def test_failure_logs_are_bounded_recovery_is_visible_and_stalled_thread_is_unhealthy(self):
        with patch.object(Maintenance, '_states', {}), patch.object(Maintenance, '_pid', os.getpid()), \
                patch('src.common.logging.log.system') as log, \
                patch('src.apps.data_factory.services.pool_maintenance.time.monotonic') as clock:
            for tick in range(40):
                clock.return_value = 100 + tick * 5
                self.assertFalse(Maintenance.run('sql', Mock(side_effect=OSError())))
                self.assertFalse(Maintenance.healthy())
            log.exception.assert_called_once()
            self.assertEqual(log.error.call_count, 3)
            Maintenance.run('sql', lambda: None)
            log.info.assert_called_once()
            self.assertTrue(Maintenance.healthy())
            clock.return_value += 60
            self.assertFalse(Maintenance.healthy())

    def test_uuid_nested_snapshot_remains_exact_and_unknown_objects_still_rejected(self):
        value = UUID('12345678-1234-5678-1234-567812345678')
        result = DataFactoryTypeCast.to_jsonable({'id': value, 'nested': ([value],)})
        self.assertEqual(json.loads(json.dumps(result)), {'id': str(value), 'nested': [[str(value)]]})
        with self.assertRaises(TypeError):
            json.dumps(DataFactoryTypeCast.to_jsonable({'unknown': object()}))


@skipUnless(os.getenv('DATASOURCE_CONTROL_MYSQL_SOAK') == '1', '显式开启 dev 只读控制连接断连长稳回归')
class ControlMySQLSoakTests(SimpleTestCase):
    def test_real_control_socket_recovery_without_business_writes(self):
        from django.conf import settings
        script = r'''
import os,time
os.environ['DJANGO_SETTINGS_MODULE']='src.settings'
import django
django.setup()
from django.conf import settings
from django.db import connections
from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum as NS
from src.apps.system.services.runtime_kv import RuntimeKV
assert settings.DATABASES['default']['NAME'].startswith('dev_'), 'dev platform only'
store=RuntimeKV.namespace(NS.DATASOURCE_GOVERNOR).independent()
start=time.monotonic()
reads=disconnects=0
ids=set()
try:
 while time.monotonic()-start<120:
  with store.control_connection():
   connection=connections[store.using]
   with connection.cursor() as cursor:
    cursor.execute('SELECT CONNECTION_ID()')
    ids.add(cursor.fetchone()[0])
   reads+=1
  if reads%10==0:
   # 仅切断本进程的控制 socket，不 KILL 其他连接、不读写共享配额或业务表。
   connection.connection._force_close()
   disconnects+=1
  time.sleep(2)
 assert reads>=50 and disconnects>=5 and len(ids)>=5
 print('readonly-control-soak-ok',reads,disconnects,len(ids))
finally:
 connections.close_all()
'''
        result = subprocess.run([sys.executable, '-c', script], cwd=settings.BASE_DIR,
                                env=dict(os.environ, DJANGO_ENV='dev'), capture_output=True, text=True, timeout=150)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('readonly-control-soak-ok', result.stdout)
