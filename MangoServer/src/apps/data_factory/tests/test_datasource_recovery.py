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
from src.apps.data_factory.services.datasource.datasource_connection import GovernedDbapiConnection
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.pool.pool_maintenance import DatasourcePoolMaintenance as Maintenance
from src.apps.data_factory.services.execution.type_cast import DataFactoryTypeCast
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
                patch('src.apps.data_factory.services.pool.pool_maintenance.time.monotonic') as clock:
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
