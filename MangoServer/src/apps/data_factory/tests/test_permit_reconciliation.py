import copy
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor

from django.test import SimpleTestCase
from django.db import OperationalError

from src.apps.data_factory.enums.performance import DatasourcePermitKindEnum
from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.data_factory.services.datasource.datasource_connection import GovernedDbapiConnection
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.recovery.permit_reconciliation import DatasourcePermitReconciliationService as Review
from src.apps.data_factory.tests.test_datasource_performance import AtomicMemoryStore


class PermitReconciliationTests(SimpleTestCase):
    def setUp(self):
        self.store = AtomicMemoryStore()
        self.receipts = {}
        self.store.get = lambda key: self.receipts.get(key)
        self.store.set = lambda key, value, ttl=None: self.receipts.update({key: value})
        self.target = SimpleNamespace(id=1, db_type=0, host='mysql.example.com', port=3306)
        for guard in (patch.object(Governor, 'store', return_value=self.store),
                      patch.object(Governor, 'policy', return_value=DatasourcePerformancePolicy()),
                      patch.object(Governor, 'configuration_guard', side_effect=lambda *args: nullcontext()),
                      patch.object(Governor, '_pending_releases', set()),
                      patch.object(Governor, '_closed_connections', set())):
            guard.start()
            self.addCleanup(guard.stop)

    def state(self):
        return next(iter(self.store.values.values()))

    def review(self, permit):
        Governor.release(permit, unknown=True)
        expected = copy.deepcopy(self.state()['permits'][permit[1]])
        return {'instance_group': permit[0], 'expected_permit': expected, 'reviewed_by': 'test-operator',
                'evidence_sha256': 'a' * 64}

    def test_unknown_operation_requires_result_and_cleanup_evidence(self):
        permit = Governor.acquire(self.target, wait=False)
        self.state()['permits'][permit[1]]['kind'] = 'operation'
        review = self.review(permit)
        with self.assertRaises(DataFactoryError):
            Review.reconcile(review, apply=True)
        review['operation_result_verified'] = True
        with self.assertRaises(DataFactoryError):
            Review.reconcile(review, apply=True)
        self.assertIn(permit[1], self.state()['permits'])
        review['cleanup_verified'] = True
        self.assertFalse(Review.reconcile(review)['reconciled'])
        self.assertIn(permit[1], self.state()['permits'])
        self.assertTrue(Review.reconcile(review, apply=True)['reconciled'])
        self.assertTrue(Review.reconcile(review, apply=True)['already_reconciled'])
        self.assertEqual(self.state()['completed'], 1)
        self.assertEqual(self.receipts[f'review:{permit[0]}:{permit[1]}']['evidence_sha256'], 'a' * 64)

    def test_connection_requires_actual_close_evidence_and_keeps_unrelated_owner(self):
        connection = Governor.acquire(self.target, wait=False)
        keep = Governor.acquire(self.target, wait=False)
        review = self.review(connection)
        with self.assertRaises(DataFactoryError):
            Review.reconcile(review, apply=True)
        review['physical_connection_closed'] = True
        Review.reconcile(review, apply=True)
        self.assertEqual(list(self.state()['permits']), [keep[1]])

    def test_changed_or_live_snapshot_cannot_be_reviewed_and_never_replays_sql(self):
        permit = Governor.acquire(self.target, wait=False)
        review = {'instance_group': permit[0], 'expected_permit': copy.deepcopy(self.state()['permits'][permit[1]]),
                  'reviewed_by': 'test-operator', 'evidence_sha256': 'b' * 64,
                  'operation_result_verified': True, 'cleanup_verified': True}
        with self.assertRaises(DataFactoryError):
            Review.reconcile(review, apply=True)
        Governor.release(permit, unknown=True)
        with self.assertRaises(DataFactoryError):
            Review.reconcile(review, apply=True)
        self.assertEqual(len(self.state()['permits']), 1)

    def test_expired_live_connection_can_only_be_released_after_real_close(self):
        permit = Governor.acquire(self.target, wait=False)
        raw = Mock()
        connection = GovernedDbapiConnection(raw, permit)
        self.store.now += 301
        self.assertEqual(Governor.renew_connections([permit]), {permit})
        self.assertIn(permit[1], self.state()['permits'])
        connection.close()
        raw.close.assert_called_once()
        self.assertFalse(self.state()['permits'])

    def test_same_hostname_pid_different_incarnation_cannot_supply_close_proof(self):
        permit = Governor.acquire(self.target, wait=False)
        process = self.state()['permits'][permit[1]]['process']
        self.state()['permits'][permit[1]]['process'] = process.rsplit(':', 1)[0] + ':' + 'f' * 32
        Governor.connection_closed(permit)
        self.assertIn(permit[1], self.state()['permits'])

    def test_receipt_write_failure_cannot_free_a_permit(self):
        permit = Governor.acquire(self.target, wait=False)
        review = {**self.review(permit), 'physical_connection_closed': True}
        with patch.object(self.store, 'set', side_effect=OperationalError(2013, 'AUTO_RECEIPT_LOST')), \
                self.assertRaises(DataFactoryError):
            Review.reconcile(review, apply=True)
        self.assertIn(permit[1], self.state()['permits'])
        self.assertFalse(self.receipts)

    def test_concurrent_reconciliation_and_lost_commit_reply_never_release_twice(self):
        permit = Governor.acquire(self.target, wait=False)
        review = {**self.review(permit), 'physical_connection_closed': True}
        update = self.store.atomic_update
        def lose_reply(*args, **kwargs):
            update(*args, **kwargs)
            raise OperationalError(2013, 'AUTO_COMMIT_REPLY_LOST')
        with patch.object(self.store, 'atomic_update', side_effect=lose_reply), self.assertRaises(DataFactoryError):
            Review.reconcile(review, apply=True)
        with ThreadPoolExecutor(max_workers=4) as workers:
            results = list(workers.map(lambda _: Review.reconcile(review, apply=True), range(4)))
        self.assertTrue(all(result['already_reconciled'] for result in results))
        self.assertEqual(self.state()['completed'], 1)

    def test_manual_statement_cannot_override_known_unfinished_factory_cleanup(self):
        from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService
        with patch.object(DataFactoryCleanupScheduleService, 'current_owner', return_value={
                'parent_case_detail_id': 7, 'parent_attempt': 2}):
            permit = Governor.acquire(self.target, wait=False)
        review = {**self.review(permit), 'operation_result_verified': True, 'cleanup_verified': True}
        with patch('src.apps.data_factory.services.governance.infrastructure.DatasourceInfrastructureService.'
                   'cleanup_review_ready', return_value=False), self.assertRaises(DataFactoryError):
            Review.reconcile(review, apply=True)
        self.assertIn(permit[1], self.state()['permits'])


class PermitReviewCommandTests(SimpleTestCase):
    def test_inspection_never_applies_a_review(self):
        from src.apps.data_factory.management.commands.reconcile_datasource_permit import Command
        with patch.object(Review, 'inspect', return_value=[]) as inspect, patch.object(Review, 'reconcile') as apply:
            Command().handle(group='a' * 32, review_file=None, apply=False)
        inspect.assert_called_once_with('a' * 32)
        apply.assert_not_called()

    def test_apply_requires_single_review_file_and_valid_group(self):
        from django.core.management.base import CommandError
        from src.apps.data_factory.management.commands.reconcile_datasource_permit import Command
        with patch.object(Review, 'inspect') as inspect, patch.object(Review, 'reconcile') as apply:
            for group in ('a' * 32, 'not-a-group'):
                with self.assertRaises(CommandError):
                    Command().handle(group=group, review_file=None, apply=True)
        inspect.assert_not_called()
        apply.assert_not_called()

    def test_review_file_defaults_to_dry_run_and_requires_explicit_apply(self):
        import json
        from src.apps.data_factory.management.commands.reconcile_datasource_permit import Command
        value = {'instance_group': 'a' * 32}
        with patch('pathlib.Path.stat', return_value=SimpleNamespace(st_size=100)), \
                patch('pathlib.Path.read_text', return_value=json.dumps(value)), \
                patch.object(Review, 'reconcile', return_value={'ready': True}) as reconcile:
            Command().handle(group='a' * 32, review_file='example.json', apply=False)
            reconcile.assert_called_once_with(value, apply=False)
