from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase
from django.utils import timezone

from src.apps.data_factory.enums.performance import DatasourcePermitKindEnum
from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.permit_reconciliation import DatasourcePermitReconciliationService as Review
from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum
from src.apps.system.models import RuntimeKVEntry
from src.apps.system.services.runtime_kv import RuntimeKV


class PermitReviewTransactionTests(TestCase):
    """真实 ORM 验证两行原子性；可在隔离 SQLite 运行，不连接业务数据源。"""
    def setUp(self):
        self.store = RuntimeKV.namespace(RuntimeKVNamespaceEnum.DATASOURCE_GOVERNOR)
        for guard in (patch.object(Governor, 'store', return_value=self.store),
                      patch.object(Governor, 'policy', return_value=DatasourcePerformancePolicy()),
                      patch.object(Governor, 'configuration_guard', side_effect=lambda *args: nullcontext()),
                      patch.object(self.store, 'control_connection', side_effect=lambda: nullcontext()),
                      patch.object(self.store, 'server_time', side_effect=timezone.now),
                      patch.object(self.store, '_now', side_effect=timezone.now),
                      patch.object(Governor, '_pending_releases', set())):
            guard.start()
            self.addCleanup(guard.stop)
        self.target = SimpleNamespace(id=1, db_type=0, host='mysql.example.com', port=3306)

    def test_receipt_and_permit_are_committed_or_rolled_back_together(self):
        permit = Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)
        Governor.release(permit, unknown=True)
        snapshot = Review.inspect(permit[0])[0]
        review = {'instance_group': permit[0], 'expected_permit': snapshot, 'reviewed_by': 'test-operator',
                  'evidence_sha256': 'a' * 64, 'physical_connection_closed': True}
        save = self.store.set
        def fail_after_receipt_write(*args, **kwargs):
            save(*args, **kwargs)
            raise OperationalError(2013, 'AUTO_AFTER_RECEIPT_WRITE')
        with patch.object(self.store, 'set', side_effect=fail_after_receipt_write), self.assertRaises(DataFactoryError):
            Review.reconcile(review, apply=True)
        self.assertEqual(Review.inspect(permit[0]), [snapshot])
        self.assertEqual(RuntimeKVEntry.objects.filter(key__startswith='review:').count(), 0)
        self.assertTrue(Review.reconcile(review, apply=True)['reconciled'])
        self.assertFalse(Review.inspect(permit[0]))
        self.assertEqual(RuntimeKVEntry.objects.filter(key__startswith='review:').count(), 1)
        self.assertTrue(Review.reconcile(review, apply=True)['already_reconciled'])
        from src.apps.system.services.system_config import SystemConfigService
        from mangotools.enums import CacheValueTypeEnum
        current = DatasourcePerformancePolicy().model_dump(mode='json')
        current['pool_size'] = 4
        previous = SimpleNamespace(value='{}', value_type=CacheValueTypeEnum.DICT.value)
        with patch('src.apps.system.services.runtime_kv.store.RuntimeKVStore.server_time', side_effect=timezone.now):
            self.assertIsNone(SystemConfigService.validate_datasource_policy_transition(previous, current))
