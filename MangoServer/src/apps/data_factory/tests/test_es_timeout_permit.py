import os
import uuid
from contextlib import contextmanager, nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.data_factory.exceptions import DataFactoryError, DATASOURCE_AUDIT_COMPLETION_FAILED, DATASOURCE_SETTLEMENT_FAILED
from src.apps.data_factory.schemas.cleanup_resource import CleanupResourceState, EsCleanupRule, EsCleanupSnapshot
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService as Resources
from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService as Errors
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
from src.apps.data_factory.services.pool.protocol_pool import ProtocolPoolRegistry as Pools
from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditHandle, SqlExecutionAuditService as Audit
from src.apps.data_factory.tests.test_datasource_performance import AtomicMemoryStore


class EsTimeoutPermitTests(SimpleTestCase):
    def setUp(self):
        self.clock = [0.0]
        self.store = AtomicMemoryStore()
        self.policy = DatasourcePerformancePolicy()
        self.target = SimpleNamespace(id=10, db_type=20, host='es.example.com', port=9200,
            extra_config={}, user='', password='', redis_db=None, update_time=timezone.now())
        self.binding = SimpleNamespace(id=9, database_id=10, database=self.target)
        self.rule = EsCleanupRule(datasource_alias_id=8, index_template='example_template_{tenant}',
                                  mode='delete_and_verify', timeout_seconds=3)
        self.snapshot = EsCleanupSnapshot(rule=self.rule, binding_id=9, connection_id=10,
            connection_version=self.target.update_time.isoformat(), environment=0,
            index='example_template_7', document_id='1001', tenant='7', baseline_absent=True)
        execution = SimpleNamespace(id=5, execution_no='DFAUTO', project_product_id=4,
                                    source_id=6, source_type=4, stage=2)
        self.item = SimpleNamespace(id=11, execution=execution, template_id=3, template=None, alias='AUTO',
            primary_value='1001', data={'tenant_id': '7', 'id': 1001},
            cleanup_resources=CleanupResourceState(snapshots=[self.snapshot], sql_cleaned=True).model_dump(mode='json'),
            save=Mock())
        self.present = True
        self.search_visible = False
        self.fail_read = False
        self.requests = []
        self.records = []
        self.client = SimpleNamespace(stream=self.stream, close=Mock())
        remember = Resources.remember_uncertainty
        self.delete_permit = None
        def observed_uncertainty(snapshot, error, permits, requests):
            result = remember(snapshot, error, permits, requests)
            if (hasattr(self, 'delete_error')
                    and self.delete_error in list(Errors.execution_error_chain(error))):
                self.delete_permit = Errors.unknown_operation_permit(error)
            return result
        for guard in (
            patch.object(Resources, 'remember_uncertainty', side_effect=observed_uncertainty),
            patch.object(Governor, 'store', return_value=self.store),
            patch.object(Governor, 'policy', return_value=self.policy),
            patch.object(Governor, 'configuration_guard', side_effect=lambda *args: nullcontext()),
            patch.object(Governor, '_pending_releases', set()),
            patch.object(Pools, '_entries', {}), patch.object(Pools, '_building', set()),
            patch.object(Pools, '_pid', os.getpid()), patch.object(Pools, '_thread', Mock()),
            patch.object(Resources, 'resolve_binding', return_value=self.binding),
            patch('src.apps.data_factory.services.cleanup.cleanup_resource.DatasourceTargetService.resolve', return_value=self.target),
            patch('src.apps.data_factory.services.protocols.elasticsearch_http.httpx.Client', return_value=self.client),
            patch('src.apps.data_factory.services.cleanup.cleanup_resource.sleep', side_effect=self.advance),
            patch('src.apps.data_factory.services.cleanup.cleanup_resource.monotonic', side_effect=lambda: self.clock[0]),
            patch.object(Audit, 'start', side_effect=self.audit),
            patch.object(Audit, 'confirm_resource_requests'),
            patch.object(Audit, 'save_completion'), patch.object(Audit, 'notify_slow'),
        ):
            guard.start()
            self.addCleanup(guard.stop)
        self.addCleanup(Pools.close_all)

    def advance(self, seconds):
        self.clock[0] += seconds
        self.store.now += seconds

    def audit(self, **kwargs):
        record = SimpleNamespace(id=len(self.records) + 1, database_id=10, datasource_type=20,
            request_id=uuid.uuid4().hex, source_stage='external_cleanup',
            source_detail={}, slow_threshold_ms=20000, save=Mock(), status='running')
        self.records.append((kwargs['sql'], record))
        return SqlExecutionAuditHandle(record, 0)

    @contextmanager
    def stream(self, method, url, **kwargs):
        self.requests.append((method, url))
        if method == 'DELETE':
            # ES 已执行条件删除，但 refresh 等待响应超时；不得再次盲删。
            self.present = False
            self.advance(1)
            try:
                raise httpx.ReadTimeout('AUTO_RESPONSE_LOST')
            except httpx.ReadTimeout as error:
                self.delete_error = error
                raise
        if self.fail_read and not self.present:
            raise httpx.ReadTimeout('AUTO_READ_UNAVAILABLE')
        present = self.present or (self.search_visible and 'realtime=false' in url)
        body = {'_id': '1001', '_index': 'example_template_7', 'found': present}
        if present:
            body.update(_source={'tenant_id': '7'}, _seq_no=4, _primary_term=1)
        response = httpx.Response(200 if present else 404, json=body, request=httpx.Request(method, url))
        yield response

    def permits(self):
        return next(iter(self.store.values.values()))['permits']

    def test_real_delete_timeout_then_full_verification_keeps_audit_without_operation_quota(self):
        unrelated = Governor.acquire(self.target)
        Governor.release(unrelated, unknown=True)
        with Infrastructure.scope():
            Infrastructure.capture(DataFactoryError(DATASOURCE_AUDIT_COMPLETION_FAILED))
            Resources.verify(self.item)
            self.assertEqual(len(Infrastructure.current()), 1)
            self.assertEqual(Infrastructure.current()[0].code, DATASOURCE_AUDIT_COMPLETION_FAILED.code)
        self.assertIsNone(self.delete_permit)
        self.assertTrue(all(value['kind'] == 'connection' for value in self.permits().values()))
        self.assertEqual(self.permits()[unrelated[1]]['state'], 'suspect')
        self.assertEqual(sum(method == 'DELETE' for method, url in self.requests), 1)
        self.assertTrue(any('realtime=false' in url for method, url in self.requests))
        self.assertGreaterEqual(self.clock[0], self.rule.timeout_seconds)
        self.assertTrue(self.item.cleanup_resources['results'][0]['success'])
        failures = [record for operation, record in self.records if record.status == 'timeout']
        self.assertEqual(len(failures), 1)
        self.assertTrue(failures[0].source_detail['outcome_unknown'])
        self.assertIn('34183', failures[0].error_message)
        self.assertIn(failures[0].request_id, Audit.confirm_resource_requests.call_args.args[0])
        Pools.close_all()
        self.assertEqual(set(self.permits()), {unrelated[1]})

    def test_search_visible_document_keeps_cleanup_failure_and_request_evidence(self):
        self.search_visible = True
        with Infrastructure.scope(), self.assertRaises(DataFactoryError):
            Resources.verify(self.item)
        self.assertTrue(self.item.cleanup_resources['uncertain_requests'])
        self.assertFalse(self.item.cleanup_resources['results'][0]['success'])
        self.assertFalse(self.item.cleanup_resources['unknown_permits'])

    def test_failed_read_persists_both_requests_without_blocking_other_sql_operations(self):
        self.fail_read = True
        with Infrastructure.scope(), self.assertRaises(DataFactoryError):
            Resources.verify(self.item)
        requests = self.item.cleanup_resources['uncertain_requests']
        self.assertEqual(len({value['request_id'] for value in requests}), 2)
        self.assertFalse(self.item.cleanup_resources['unknown_permits'])
        self.assertFalse(self.item.cleanup_resources['results'][0]['success'])

    def test_verification_audit_failure_does_not_replay_delete_on_cleanup_retry(self):
        with Infrastructure.scope(), patch.object(Audit, 'confirm_resource_requests',
                side_effect=DataFactoryError(DATASOURCE_AUDIT_COMPLETION_FAILED)):
            with self.assertRaises(DataFactoryError):
                Resources.verify(self.item)
        retry_started = self.clock[0]
        with Infrastructure.scope():
            Resources.verify(self.item)
        self.assertGreaterEqual(self.clock[0] - retry_started, self.rule.timeout_seconds)
        self.assertEqual(sum(method == 'DELETE' for method, url in self.requests), 1)

    def test_checkpoint_keeps_read_timeout_request_evidence_for_recovery(self):
        from datetime import datetime, timezone as dt_timezone
        self.present = False
        self.fail_read = True
        with Infrastructure.scope(), self.assertRaises(DataFactoryError):
            Resources.advance(self.item, generation=0, task_id=1,
                clock=lambda: datetime.fromtimestamp(1800000000 + self.clock[0], dt_timezone.utc))
        self.assertEqual(len(self.item.cleanup_resources['uncertain_requests']), 1)
        self.assertFalse(self.item.cleanup_resources['unknown_permits'])
        self.assertFalse(self.item.cleanup_resources['results'])

    def test_explicit_chain_lookup_is_bounded_and_does_not_copy_private_fields(self):
        original = TimeoutError()
        original._datasource_unknown_permit = ('a' * 32, 'b' * 32)
        original.password = 'AUTO_PRIVATE'
        wrapped = TimeoutError()
        wrapped.__cause__ = original
        original.__cause__ = wrapped
        final = Errors.preserve_execution_state(wrapped, TimeoutError())
        self.assertEqual(final._datasource_unknown_permit, ('a' * 32, 'b' * 32))
        self.assertFalse(hasattr(final, 'password'))
        self.assertIsNone(Errors.unknown_operation_permit(TimeoutError()))
