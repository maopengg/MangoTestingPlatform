import hashlib
import os
import threading
import time
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import OperationalError
from django.test import SimpleTestCase
from pymysql import OperationalError as MysqlOperationalError

from src.apps.data_factory.enums.performance import DatasourceQueueLaneEnum
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy, MysqlOperationSession
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.recovery.mysql_session_recovery import MysqlSessionRecoveryService as Sessions
from src.apps.data_factory.services.recovery.permit_reconciliation import DatasourcePermitReconciliationService as Reconcile
from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditHandle, SqlExecutionAuditService as Audit
from src.apps.data_factory.tests.test_datasource_performance import AtomicMemoryStore


class MysqlSessionRecoveryTests(SimpleTestCase):
    def setUp(self):
        self.store = AtomicMemoryStore()
        self.store.now = time.time()
        self.store.name = 'datasource_governor'
        self.target = SimpleNamespace(id=49, db_type=0, host='mysql.example.com', port=3306, cache_key='c'*40)
        self.session = MysqlOperationSession(server_uuid='11111111-1111-1111-1111-111111111111', session_id=123,
            target_key=self.target.cache_key, account_digest=hashlib.sha256(b'AUTO_user@%').hexdigest())
        self.record = SimpleNamespace(id=77, source_detail={'outcome_unknown': True}, status='fail', database_id=49,
            request_id='a'*32, datasource_alias_id=3, project_product_id=1, test_env=0)
        self.handle = SqlExecutionAuditHandle(self.record, time.perf_counter())
        for guard in (
            patch.object(Governor, 'store', return_value=self.store),
            patch.object(Governor, 'policy', return_value=DatasourcePerformancePolicy()),
            patch.object(Governor, 'lane', return_value=DatasourceQueueLaneEnum.NORMAL),
            patch.object(Governor, 'configuration_guard', side_effect=lambda *args: nullcontext()),
            patch.object(Governor, '_pending_releases', set()),
            patch.object(Governor, '_closed_pid', os.getpid()),
            patch.object(Audit, 'save_completion'),
            patch('src.apps.data_factory.selectors.execution_audit.ExecutionAuditSelector.permit_evidence',
                  return_value={77: self.record}),
        ):
            guard.start()
            self.addCleanup(guard.stop)
        self.group = Governor.target_policy(self.target)[2]

    def state(self):
        return self.store.values[f'group:{self.group}:control']

    def test_deferred_audit_keeps_request_link_for_monitor_and_retention(self):
        self.record.id = None
        with Audit.scope(self.handle):
            permit = Governor.acquire(self.target)
        saved = self.state()['permits'][permit[1]]
        self.assertNotIn('audit_record_id', saved)
        self.assertEqual(saved['audit_request_id'], self.record.request_id)
        Governor.finish_connection(permit, unknown=True)
        self.record.id = 77
        self.store.scan = Mock(return_value={'items': [{'key': f'group:{self.group}:control'}], 'next_cursor': None})
        with patch('src.apps.data_factory.selectors.execution_audit.ExecutionAuditSelector.request_evidence',
                   return_value={self.record.request_id: self.record}) as evidence, \
                patch('src.apps.data_factory.services.recovery.health_incident.DatasourceHealthIncidentService.safe_observe'), \
                self.assertLogs('system', level='WARNING'):
            result = Reconcile.monitor()
        self.assertEqual(result['groups'][0]['permits'][0]['audit']['request_id'], self.record.request_id)
        evidence.assert_called_once_with({self.record.request_id})
        self.assertIn(permit[1], self.state()['permits'])
        with patch('src.apps.system.selectors.runtime_kv.RuntimeKVSelector.entries', return_value=[
                SimpleNamespace(value={'data': self.state()})]), \
                patch('src.apps.data_factory.selectors.execution_audit.ExecutionAuditSelector.request_evidence',
                      return_value={self.record.request_id: self.record}):
            self.assertEqual(Reconcile.referenced_audit_ids(), {77})

    def unknown(self, session=True):
        import uuid
        from src.apps.data_factory.schemas.performance import DatasourcePermit
        owner = uuid.uuid4().hex
        def historical(state, now):
            state.permits[owner] = DatasourcePermit(owner=owner, process='old-worker', lane='normal',
                kind='operation', state='suspect', created_at=now-10, expires_at=now-1, audit_record_id=77,
                mysql_session=self.session if session else None)
        Governor.change(self.group, historical)
        permit = self.group, owner
        return permit

    def test_confirmed_session_end_releases_exact_operation_not_business_result(self):
        original = self.unknown()
        keep = self.unknown(session=False)
        with patch.object(Sessions, 'probe', return_value=True):
            self.assertEqual(Sessions.recover_group(self.group), 1)
        self.assertNotIn(original[1], self.state()['permits'])
        self.assertIn(keep[1], self.state()['permits'])
        self.assertTrue(self.record.source_detail['outcome_unknown'])
        self.assertEqual(self.record.status, 'fail')
        self.assertEqual(self.record.source_detail['physical_session_recovery']['basis'], 'server_session_absent')

    def physical(self):
        permit = Governor.acquire(self.target)
        Governor.bind_mysql_connection(permit, self.session, self.record.id)
        self.store.now += Governor.CONNECTION_LEASE_SECONDS + 1
        return permit

    def test_physical_connection_without_close_proof_is_recovered_only_after_session_absence(self):
        original = self.physical()
        self.assertFalse(any(key.startswith('closed:') for key in self.store.values))
        with patch.object(Sessions, 'probe', return_value=True):
            self.assertEqual(Sessions.recover_group(self.group), 1)
            self.assertEqual(Sessions.recover_group(self.group), 0)
        self.assertNotIn(original[1], self.state()['permits'])
        self.assertEqual(self.record.status, 'fail')
        self.assertTrue(self.record.source_detail['outcome_unknown'])
        self.assertNotIn('completed_operation_permits', self.record.source_detail)

    def test_sigkill_worker_without_close_proof_recovers_frozen_session_not_business_result(self):
        import json
        import subprocess
        import sys
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(prefix='mango-killed-worker-') as directory:
            output = Path(directory) / 'worker.log'
            with output.open('w') as stream:
                child = subprocess.Popen([sys.executable, '-m',
                    'src.apps.data_factory.tests.permit_recovery_worker_fixture', '--without-close'],
                    stdout=stream, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 10
                snapshot = None
                while time.monotonic() < deadline and child.poll() is None:
                    line = next((line for line in output.read_text().splitlines()
                                 if line.startswith('PERMIT_RECOVERY_FIXTURE=')), None)
                    if line:
                        snapshot = json.loads(line.split('=', 1)[1])['values']
                        break
                    time.sleep(0.02)
                self.assertIsNotNone(snapshot, 'Worker must persist identity before the kill')
                child.kill()
                child.wait(timeout=3)
                self.assertLess(child.returncode, 0)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=3)
        self.store.values = snapshot
        self.store.now = time.time() + Governor.CONNECTION_LEASE_SECONDS + 1
        self.assertFalse(any(key.startswith('closed:') for key in snapshot))
        original = next(iter(self.state()['permits'].values()))
        self.assertEqual(original['kind'], 'connection')
        self.assertEqual(original['mysql_session'], self.session.model_dump(mode='json'))
        with patch.object(Sessions, 'probe', return_value=True):
            self.assertEqual(Sessions.recover_group(self.group), 1)
        self.assertFalse(self.state()['permits'])
        self.assertTrue(self.record.source_detail['outcome_unknown'])
        self.assertEqual(self.record.status, 'fail')

    def test_physical_connection_still_present_or_probe_failed_is_retained(self):
        original = self.physical()
        for result in (False, OperationalError(2013, 'AUTO_NETWORK_UNAVAILABLE')):
            self.store.now += 6
            with patch.object(Sessions, 'probe') as probe:
                probe.side_effect = result if isinstance(result, Exception) else None
                probe.return_value = result
                self.assertEqual(Sessions.recover_group(self.group), 0)
                self.assertIn(original[1], self.state()['permits'])
        self.assertFalse(any(key.startswith('closed:') for key in self.store.values))

    def test_session_change_during_probe_cannot_release_the_new_session(self):
        original = self.physical()
        def replaced(*args):
            self.state()['permits'][original[1]]['mysql_session']['session_id'] += 1
            return True
        with patch.object(Sessions, 'probe', side_effect=replaced):
            self.assertEqual(Sessions.recover_group(self.group), 0)
        self.assertIn(original[1], self.state()['permits'])

    def test_physical_session_proof_survives_settlement_outage_and_is_idempotent(self):
        original = self.physical()
        with patch.object(Sessions, 'probe', return_value=True), \
                patch.object(Reconcile, 'recover_closed_connections', side_effect=OperationalError(2013, 'AUTO_LOST')):
            self.assertEqual(Sessions.recover_group(self.group), 0)
        proof = self.store.get(f'closed:{self.group}:{original[1]}')
        self.assertEqual(proof['basis'], 'server_session_absent')
        self.assertEqual(Reconcile.recover_closed_connections(self.group), 1)
        self.assertEqual(Reconcile.recover_closed_connections(self.group), 0)

    def test_physical_session_proof_does_not_release_a_renewed_active_owner(self):
        original = self.physical()
        with patch.object(Sessions, 'probe', return_value=True), \
                patch.object(Reconcile, 'recover_closed_connections', return_value=0):
            self.assertEqual(Sessions.recover_group(self.group), 0)
        self.state()['permits'][original[1]]['expires_at'] = self.store.now + 300
        self.assertEqual(Reconcile.recover_closed_connections(self.group), 0)
        self.assertIn(original[1], self.state()['permits'])

    def test_still_running_or_unavailable_probe_never_releases(self):
        original = self.unknown()
        for result in (False, OperationalError(2013, 'AUTO_PRIVATE')):
            with self.subTest(result=type(result).__name__), patch.object(Sessions, 'probe') as probe:
                probe.side_effect = result if isinstance(result, Exception) else None
                probe.return_value = result
                self.store.now += 6
                self.assertEqual(Sessions.recover_group(self.group), 0)
                self.assertIn(original[1], self.state()['permits'])
        self.assertNotIn('completed_operation_permits', self.record.source_detail)

    def test_missing_historical_session_proof_cannot_be_fabricated(self):
        original = self.unknown(session=False)
        with patch.object(Sessions, 'probe') as probe:
            self.assertEqual(Sessions.recover_group(self.group), 0)
        probe.assert_not_called()
        self.assertIn(original[1], self.state()['permits'])

    def test_session_evidence_survives_lost_settlement_and_process_rebuild(self):
        original = self.unknown()
        change = Governor.change
        def fail_settle(group, callback, **kwargs):
            if callback.__name__ == 'settle':
                raise OperationalError(2013, 'AUTO_CONTROL_LOST')
            return change(group, callback, **kwargs)
        with patch.object(Sessions, 'probe', return_value=True), patch.object(Governor, 'change', side_effect=fail_settle):
            self.assertEqual(Sessions.recover_group(self.group), 0)
        self.assertIn(original[1], self.state()['permits'])
        self.store.now += 1
        self.assertEqual(Reconcile.recover_confirmed(self.group), 1)
        self.assertEqual(Reconcile.recover_confirmed(self.group), 0)

    def test_live_oldest_session_does_not_starve_other_unknown_sessions(self):
        first, second = self.unknown(), self.unknown()
        with patch.object(Sessions, 'probe', side_effect=[False, True]):
            self.assertEqual(Sessions.recover_group(self.group), 0)
            self.store.now += 6
            self.assertEqual(Sessions.recover_group(self.group), 1)
        self.assertIn(first[1], self.state()['permits'])
        self.assertNotIn(second[1], self.state()['permits'])

    def test_cross_consumer_lease_prevents_duplicate_probe(self):
        self.unknown()
        entered, finish = threading.Event(), threading.Event()
        def probe(*args):
            entered.set()
            finish.wait(2)
            return True
        result = []
        with patch.object(Sessions, 'probe', side_effect=probe) as mocked:
            worker = threading.Thread(target=lambda: result.append(Sessions.recover_group(self.group)))
            worker.start()
            try:
                self.assertTrue(entered.wait(1))
                self.assertEqual(Sessions.recover_group(self.group), 0)
            finally:
                finish.set()
                worker.join(3)
        mocked.assert_called_once()
        self.assertEqual(result, [1])

    def test_probe_requires_same_server_account_self_visibility_and_absent_original(self):
        from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasource
        good = (self.session.server_uuid, 0, 1, 'AUTO_user@%', 456)
        rows = [good, ('22222222-2222-2222-2222-222222222222', *good[1:]),
                (good[0], 1, *good[2:]), (good[0], 0, 0, *good[3:]),
                (good[0], 0, 1, 'OTHER@%', 456), (*good[:4], 789)]
        for row in rows:
            with self.subTest(row=row), patch.object(Sessions, 'target', return_value=self.target), \
                    patch.object(DataFactoryDatasource, '_create_engine') as engines, \
                    patch.object(Sessions, '_query', return_value=row) as query:
                engines.return_value.connect.return_value.__enter__.return_value.connection.driver_connection._connection.thread_id.return_value = 456
                def checked(*args, **kwargs):
                    self.assertFalse(Governor.admission_wait_enabled())
                    return row
                query.side_effect = checked
                self.assertEqual(Sessions.probe(self.record, self.session), row == good)
        self.assertTrue(Governor.admission_wait_enabled())

    def test_changed_binding_or_query_permission_prevents_probe(self):
        from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasourceResolver as Resolver
        from src.apps.data_factory.services.datasource.datasource_target import DatasourceTargetService
        with patch.object(Resolver, 'resolve_binding_by_env'), patch.object(Resolver, 'require_binding_permission'), \
                patch.object(DatasourceTargetService, 'resolve', return_value=SimpleNamespace(cache_key='d'*40, db_type=0)):
            self.assertIsNone(Sessions.target(self.record, self.session))

    def test_capture_is_once_per_connection_and_restores_timeout(self):
        raw = SimpleNamespace(_connection=SimpleNamespace(_read_timeout=120, thread_id=lambda: 123))
        def read(*args, **kwargs):
            self.assertEqual(raw._connection._read_timeout, 120)
            return self.session.server_uuid, 123, 'AUTO_user@%'
        with patch.object(Sessions, '_query', side_effect=read) as query:
            self.assertEqual(Sessions.capture(self.target, raw), self.session)
            self.assertEqual(Sessions.capture(self.target, raw), self.session)
        query.assert_called_once()
        self.assertEqual(raw._connection._read_timeout, 120)

    def test_connection_session_identity_is_persisted_before_the_connection_is_returned(self):
        from src.apps.data_factory.services.datasource.datasource_connection import GovernedDbapiConnection
        cursor = Mock()
        cursor.fetchone.return_value = (self.session.server_uuid, 123, 'AUTO_user@%')
        native = SimpleNamespace(thread_id=lambda: 123, _read_timeout=120,
                                 cursor=lambda: cursor, close=Mock())
        with patch.object(Audit, 'start', return_value=self.handle), patch.object(Audit, 'finish_success'):
            connection = GovernedDbapiConnection.connect(self.target, lambda: native)
        frozen = next(iter(self.state()['permits'].values()))
        self.assertEqual(frozen['kind'], 'connection')
        self.assertEqual(frozen['mysql_session'], self.session.model_dump(mode='json'))
        self.assertEqual(frozen['audit_record_id'], 77)
        cursor.execute.assert_called_once_with(Sessions.IDENTITY_SQL, None)
        self.assertEqual(native._read_timeout, 120)
        native.close.assert_not_called()
        connection.close()
        self.assertFalse(self.state()['permits'])

    def test_identity_persistence_failure_closes_before_any_business_use(self):
        from src.apps.data_factory.services.datasource.datasource_connection import GovernedDbapiConnection
        cursor = Mock()
        cursor.fetchone.return_value = (self.session.server_uuid, 123, 'AUTO_user@%')
        native = SimpleNamespace(thread_id=lambda: 123, _read_timeout=120,
                                 cursor=lambda: cursor, close=Mock())
        with patch.object(Audit, 'start', return_value=self.handle), patch.object(Audit, 'finish_success'), \
                patch.object(Governor, 'bind_mysql_connection', side_effect=OperationalError(2013, 'AUTO_LOST')):
            with self.assertRaises(OperationalError):
                GovernedDbapiConnection.connect(self.target, lambda: native)
        native.close.assert_called_once()
        self.assertFalse(self.state()['permits'])

    def test_unsupported_server_identity_does_not_disable_case_execution(self):
        raw = SimpleNamespace(_connection=SimpleNamespace(_read_timeout=120, thread_id=lambda: 123))
        with patch.object(Sessions, '_query', side_effect=MysqlOperationalError(1193, 'AUTO_UNSUPPORTED')) as query:
            self.assertIsNone(Sessions.capture(self.target, raw))
            self.assertIsNone(Sessions.capture(self.target, raw))
        query.assert_called_once()
        self.assertEqual(raw._connection._read_timeout, 120)

    def test_nonblocking_recovery_cannot_exceed_existing_capacity(self):
        # 不额外增加连接或并发预算；满额时核查也必须退让。
        policy = Governor.policy()
        count = policy.mysql.connections - policy.pool_size
        permits = [Governor.acquire(self.target, wait=False) for _ in range(count)]
        from src.apps.data_factory.exceptions import DataFactoryError
        with Governor.nonblocking_admission(), self.assertRaises(DataFactoryError):
            Governor.acquire(self.target)
        for permit in permits:
            Governor.release(permit)

    def test_read_only_probe_queries_are_audited_and_cursor_is_closed_on_failure(self):
        raw, cursor = Mock(), Mock()
        raw.cursor.return_value = cursor
        cursor.execute.side_effect = MysqlOperationalError(1193, 'AUTO_UNSUPPORTED')
        with patch.object(Audit, 'start', return_value=self.handle), patch.object(Audit, 'finish_failure') as failed:
            with self.assertRaises(MysqlOperationalError):
                Sessions._query(self.target, raw, Sessions.IDENTITY_SQL, (), recovery=False)
        cursor.close.assert_called_once()
        failed.assert_called_once()
        self.assertFalse(self.store.values)

    def test_background_tick_is_bounded_and_keeps_scan_cursor(self):
        self.unknown()
        self.store.using = 'default'
        key = f'group:{self.group}:control'
        row = SimpleNamespace(id=42, key=key, value={'data': self.state()})
        with patch.object(self.store, 'control_connection', create=True, side_effect=lambda: nullcontext()), \
                patch.object(self.store, 'scan', create=True,
                    return_value={'items': [{'key': key}], 'next_cursor': 43}) as scan, \
                patch('src.apps.system.selectors.runtime_kv.RuntimeKVSelector.entries', return_value=[row]), \
                patch.object(Reconcile, 'recover_confirmed', return_value=1), \
                patch.object(Sessions, 'recover_group', return_value=0):
            self.assertEqual(Sessions.tick(30), {'next_cursor': 42, 'recovered': 1})
        scan.assert_called_once_with(prefix='group:', after_id=30, page_size=10)

    def test_capture_does_not_hide_internal_audit_errors(self):
        raw = SimpleNamespace(_connection=SimpleNamespace(_read_timeout=120, thread_id=lambda: 123))
        with patch.object(Sessions, '_query', side_effect=AttributeError('AUTO_AUDIT_BUG')):
            with self.assertRaises(AttributeError):
                Sessions.capture(self.target, raw)
        self.assertEqual(raw._connection._read_timeout, 120)
