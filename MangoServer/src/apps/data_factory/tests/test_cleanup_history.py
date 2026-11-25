from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from threading import RLock
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.apps import apps
from django.test import SimpleTestCase

from src.apps.auto_api.services.resource_cleanup.resource_cleanup import ApiResourceCleanupService as ApiCleanup
from src.apps.auto_api.tests.test_resource_cleanup import proof_data
from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.schemas.cleanup_history import CleanupEventEvidence, CleanupHistoryEntry
from src.apps.data_factory.schemas.cleanup_resource import CleanupResourceState
from src.apps.data_factory.selectors.cleanup_history import ResourceCleanupHistorySelector as Selector
from src.apps.data_factory.services.cleanup.cleanup_history import ResourceCleanupHistoryService as History
from src.apps.data_factory.services.cleanup.cleanup_persistence import CleanupPersistenceService as Persistence
from src.apps.auto_api.exceptions import AutoApiError


def entry(number, kind='failed', **evidence):
    return CleanupHistoryEntry(id=f'{number:032x}', create_time='2026-11-17T10:00:00+00:00',
        operator_id=4, kind=kind, evidence=CleanupEventEvidence(**evidence)).model_dump(mode='json', exclude_none=True)


class CleanupHistoryTests(SimpleTestCase):
    def atomic_memory(self):
        # 模拟控制库事务的串行行锁；不连接业务库，不代替真实数据库集成验收。
        stack = ExitStack()
        self.addCleanup(stack.close)
        lock = RLock()
        stack.enter_context(patch('django.db.transaction.Atomic.__enter__', lambda scope: lock.acquire()))
        stack.enter_context(patch('django.db.transaction.Atomic.__exit__', lambda scope, *error: lock.release() and None))
        return stack

    def test_no_new_model_and_old_snapshots_have_empty_history(self):
        self.assertFalse(any(model._meta.db_table == 'resource_cleanup_event' for model in apps.get_models()))
        self.assertEqual(CleanupResourceState.model_validate({}).cleanup_history, [])
        self.assertEqual(proof_data().cleanup_history, [])

    def test_old_state_cannot_remove_authorization_or_failure_and_retry_is_idempotent(self):
        failure = entry(1, message='AUTO precise original failure ' * 300)
        grant = entry(2, 'compensation_authorized', authorization_digest='a' * 64,
            snapshot_digest='b' * 64)
        stored = {'snapshots': [], 'cleanup_history': [failure, grant]}
        before = deepcopy(stored)
        merged = History.merge(stored, {'sql_cleaned': True, 'cleanup_history': []}, entry(3, 'succeeded'))
        self.assertEqual(History.merge(merged, merged, entry(3, 'succeeded')), merged)
        self.assertEqual(stored, before)
        self.assertEqual([value['kind'] for value in merged['cleanup_history']],
            ['failed', 'compensation_authorized', 'succeeded'])
        self.assertEqual(merged['cleanup_history'][0]['evidence']['message'], failure['evidence']['message'])
        self.assertEqual(merged['cleanup_history'][1]['evidence']['authorization_digest'], 'a' * 64)

    def test_invalid_history_is_not_silently_discarded(self):
        for history in ('invalid', [{'id': 'invalid'}], [entry(1), entry(1)]):
            with self.subTest(history=history), self.assertRaises(DataFactoryError):
                History.merge({'cleanup_history': history}, {'sql_cleaned': True})

    def test_compensation_and_api_recovery_evidence_roundtrip_without_loosening_schema(self):
        from pydantic import ValidationError
        from src.apps.data_factory.schemas.cleanup_resource import EsCleanupCompensation
        from src.apps.auto_api.schemas.resource_cleanup import ApiResourceRecoveryEvidence, ApiResourceEsIdentityMapping
        compensation = EsCleanupCompensation(snapshot_index=0, snapshot_digest='a' * 64,
            operator_id=4, authorized_at='2026-11-17T10:00:00+00:00', reason='AUTO approved recovery',
            seq_no=71, primary_term=3)
        recovery = ApiResourceRecoveryEvidence(identity_mapping=ApiResourceEsIdentityMapping(
            es_business_id_path='projects[].projectId', es_version_path='projects[].projectVersion'))
        event = entry(1, 'compensation_authorized', compensation=compensation, api_recovery=recovery)
        reread = CleanupHistoryEntry.model_validate(event).model_dump(mode='json', exclude_none=True)
        self.assertEqual(reread['evidence']['compensation']['seq_no'], 71)
        self.assertEqual(reread['evidence']['api_recovery']['identity_mapping']['es_business_id_path'], 'projects[].projectId')
        self.assertEqual(CleanupResourceState.model_validate({'cleanup_history': [event]}).cleanup_history[0].id, event['id'])
        with self.assertRaises(ValidationError):
            CleanupEventEvidence(compensation={**compensation.model_dump(), 'skip_ownership': True})

    def test_factory_concurrent_appends_and_stale_checkpoint_saves_keep_all_events(self):
        from src.apps.data_factory.models import DataFactoryExecutionItem
        stack = self.atomic_memory()
        stored = {'snapshots': [], 'cleanup_history': []}
        manager = stack.enter_context(patch('src.apps.data_factory.models.DataFactoryExecutionItem.objects'))
        def get(**kwargs):
            row = SimpleNamespace(cleanup_resources=deepcopy(stored))
            row.save = lambda **kwargs: stored.update(deepcopy(row.cleanup_resources))
            return row
        manager.select_for_update.return_value.only.return_value.get.side_effect = get
        def worker(number):
            item = DataFactoryExecutionItem(id=4, cleanup_resources={'snapshots': []})
            item.save = Mock(side_effect=lambda **kwargs: stored.update(deepcopy(item.cleanup_resources)))
            History.append_factory(item, entry(number))
            # 保存的是清理开始前的旧对象；不得覆盖其他线程刚追加的证据。
            item.cleanup_resources = {'snapshots': [], 'sql_cleaned': True}
            Persistence.save(item, ['cleanup_resources'])
        with ThreadPoolExecutor(max_workers=10) as pool:
            list(pool.map(worker, range(1, 41)))
        self.assertEqual(len(stored['cleanup_history']), 40)
        self.assertEqual({value['id'] for value in stored['cleanup_history']}, {f'{n:032x}' for n in range(1, 41)})
        self.assertTrue(stored['sql_cleaned'])

    def test_api_persist_merges_latest_history_and_clearing_error_preserves_evidence(self):
        stack = self.atomic_memory()
        proof = proof_data()
        stored = proof.model_dump(mode='json')
        stored['cleanup_history'] = [entry(1, message='AUTO initial cleanup failure')]
        record = SimpleNamespace(id=8, cleanup_token='AUTO_owner', proof=deepcopy(stored))
        manager = stack.enter_context(patch('src.apps.auto_api.services.resource_cleanup.resource_cleanup.ApiCaseExecutionResource.objects'))
        query = manager.filter.return_value
        query.filter.return_value = query
        query.select_for_update.return_value.only.return_value.first.side_effect = lambda: SimpleNamespace(proof=deepcopy(stored))
        def update(**changes):
            stored.clear()
            stored.update(deepcopy(changes['proof']))
            return 1
        query.update.side_effect = update
        ApiCleanup.persist(record, proof, _history_entry=entry(2, 'compensation_authorized', authorization_digest='a' * 64))
        proof.cleanup_history = []
        ApiCleanup.persist(record, proof, _history_entry=entry(3, 'succeeded'), error_message='')
        self.assertEqual([value['kind'] for value in stored['cleanup_history']],
            ['failed', 'compensation_authorized', 'succeeded'])
        self.assertEqual(record.error_message, '')
        self.assertEqual(len(proof.cleanup_history), 3)
        query.select_for_update.return_value.only.return_value.first.return_value = None
        query.select_for_update.return_value.only.return_value.first.side_effect = None
        count = query.update.call_count
        with self.assertRaises(AutoApiError):
            ApiCleanup.persist(record, proof)
        self.assertEqual(query.update.call_count, count)

    def test_history_page_has_stable_unique_keys_and_never_returns_all_by_default(self):
        rows = [{**entry(n), 'factory_item_id': n % 2 + 4, 'api_resource_id': None} for n in range(1, 26)]
        first, second = Selector.page(rows, 1, 10), Selector.page(rows, 2, 10)
        self.assertEqual(first['count'], 25)
        self.assertEqual(len(first['items']), 10)
        self.assertTrue(set(value['id'] for value in first['items']).isdisjoint(value['id'] for value in second['items']))
        self.assertIn('kind_label', first['items'][0])
