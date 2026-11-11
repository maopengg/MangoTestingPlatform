from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.exceptions import EmptyResultSet
from django.db.models.signals import post_delete, post_save
from django.test import SimpleTestCase

from src.apps.auto_api.models import ApiPublic
from src.apps.auto_ui.models import UiPublic
from src.common.utils.variable_tag_cache import VariableTagSummaryCache


class PublicVariableTagCacheTests(SimpleTestCase):
    def setUp(self):
        self.values = {}
        self.writes = []
        self.cache = Mock()
        self.cache.get.side_effect = lambda key: self.values.get(key)
        self.cache.add.side_effect = self.add
        self.cache.set.side_effect = self.set
        cache_patch = patch('src.common.utils.variable_tag_cache.cache', self.cache)
        cache_patch.start()
        self.addCleanup(cache_patch.stop)
        self.connections = {name: SimpleNamespace(in_atomic_block=False) for name in ('default', 'other')}
        connection_patch = patch('src.common.utils.variable_tag_cache.connections', self.connections)
        connection_patch.start()
        self.addCleanup(connection_patch.stop)

    def add(self, key, value, timeout):
        if key not in self.values:
            self.set(key, value, timeout)
            return True
        return False

    def set(self, key, value, timeout):
        self.values[key] = value
        self.writes.append((key, timeout))

    def query(self, *, scope=(1,), keyword='', model='auto_api.apipublic', using='default'):
        query = Mock(db=using, model=SimpleNamespace(_meta=SimpleNamespace(label_lower=model)))
        compiler = query.order_by.return_value.values.return_value.query.get_compiler.return_value
        compiler.as_sql.return_value = ('SELECT id FROM public_variable WHERE scope=%s AND name=%s', (scope, keyword))
        return query

    def summary(self, total):
        return {'total': total, 'untagged': total, 'items': []}

    def test_repeated_query_hits_60_second_cache_and_only_stores_summary(self):
        query = self.query(keyword='private-search')
        loader = Mock(return_value=self.summary(3))
        self.assertEqual(VariableTagSummaryCache.get(query, loader), self.summary(3))
        self.assertEqual(VariableTagSummaryCache.get(query, loader), self.summary(3))
        loader.assert_called_once_with()
        keys = [key for key, timeout in self.writes if ':summary:' in key]
        self.assertEqual(len(keys), 1)
        self.assertNotIn('private-search', keys[0])
        self.assertIn((keys[0], 60), self.writes)
        self.assertEqual(self.values[keys[0]], self.summary(3))

    def test_permissions_filters_protocols_and_database_aliases_are_isolated(self):
        loader = Mock(side_effect=[self.summary(i) for i in range(1, 6)])
        queries = [self.query(scope=(1, 2)), self.query(scope=(1,)), self.query(keyword='filter'),
                   self.query(model='auto_ui.uipublic'), self.query(using='other')]
        for index, query in enumerate(queries, 1):
            self.assertEqual(VariableTagSummaryCache.get(query, loader), self.summary(index))
        self.assertEqual(loader.call_count, 5)
        for index, query in enumerate(queries, 1):
            self.assertEqual(VariableTagSummaryCache.get(query, loader), self.summary(index))
        self.assertEqual(loader.call_count, 5)

    def test_invalidation_after_commit_covers_all_filters_but_not_other_protocol(self):
        api, filtered, ui = self.query(), self.query(keyword='filter'), self.query(model='auto_ui.uipublic')
        for query in (api, filtered, ui):
            VariableTagSummaryCache.get(query, lambda: self.summary(1))
        callbacks = []
        with patch('src.common.utils.variable_tag_cache.transaction.on_commit',
                   side_effect=lambda callback, using: callbacks.append(callback)) as on_commit:
            VariableTagSummaryCache.invalidate_after_commit('auto_api.apipublic')
        on_commit.assert_called_once()
        self.assertEqual(VariableTagSummaryCache.get(api, lambda: self.summary(2)), self.summary(1))
        callbacks[0]()
        for query in (api, filtered):
            self.assertEqual(VariableTagSummaryCache.get(query, lambda: self.summary(2)), self.summary(2))
        self.assertEqual(VariableTagSummaryCache.get(ui, lambda: self.summary(2)), self.summary(1))

    def test_late_reader_cannot_repopulate_new_revision_with_pre_commit_summary(self):
        query = self.query()

        def stale_read():
            VariableTagSummaryCache.invalidate('auto_api.apipublic')
            return self.summary(1)

        VariableTagSummaryCache.get(query, stale_read)
        self.assertEqual(VariableTagSummaryCache.get(query, lambda: self.summary(2)), self.summary(2))

    def test_lost_revision_marker_cannot_resurrect_old_entries(self):
        query = self.query()
        VariableTagSummaryCache.get(query, lambda: self.summary(1))
        self.values.pop(VariableTagSummaryCache.revision_key('auto_api.apipublic', 'default'))
        self.assertEqual(VariableTagSummaryCache.get(query, lambda: self.summary(2)), self.summary(2))

    def test_uncommitted_queries_bypass_shared_cache(self):
        query = self.query()
        VariableTagSummaryCache.get(query, lambda: self.summary(1))
        self.connections['default'].in_atomic_block = True
        self.assertEqual(VariableTagSummaryCache.get(query, lambda: self.summary(9)), self.summary(9))
        self.connections['default'].in_atomic_block = False
        self.assertEqual(VariableTagSummaryCache.get(query, lambda: self.summary(2)), self.summary(1))

    def test_cache_outage_does_not_hide_database_result_or_break_invalidation(self):
        self.cache.get.side_effect = RuntimeError('cache-unavailable')
        self.assertEqual(VariableTagSummaryCache.get(self.query(), lambda: self.summary(1)), self.summary(1))
        self.cache.set.side_effect = RuntimeError('cache-unavailable')
        VariableTagSummaryCache.invalidate('auto_api.apipublic')

    def test_failed_query_is_not_cached(self):
        query = self.query()
        with self.assertRaises(RuntimeError):
            VariableTagSummaryCache.get(query, Mock(side_effect=RuntimeError('database-unavailable')))
        self.assertFalse(any(':summary:' in key for key in self.values))

    def test_cache_write_failure_preserves_successful_query_result(self):
        query = self.query()
        VariableTagSummaryCache.get(query, lambda: self.summary(1))
        VariableTagSummaryCache.invalidate('auto_api.apipublic')
        self.cache.set.side_effect = RuntimeError('cache-unavailable')
        self.assertEqual(VariableTagSummaryCache.get(query, lambda: self.summary(2)), self.summary(2))

    def test_empty_permission_scope_returns_empty_summary_without_loading(self):
        query = self.query(scope=())
        compiler = query.order_by.return_value.values.return_value.query.get_compiler.return_value
        compiler.as_sql.side_effect = EmptyResultSet
        loader = Mock()
        self.assertEqual(VariableTagSummaryCache.get(query, loader), self.summary(0))
        loader.assert_not_called()
        self.cache.get.assert_not_called()

    def test_model_signals_cover_page_mcp_status_and_batch_save_paths(self):
        with patch.object(VariableTagSummaryCache, 'invalidate_after_commit') as invalidate:
            for model in (ApiPublic, UiPublic):
                for created in (True, False):
                    post_save.send(sender=model, instance=model(), created=created, raw=False,
                                   using='default', update_fields=None)
                post_delete.send(sender=model, instance=model(), using='default')
        self.assertEqual(invalidate.call_count, 6)
        labels = [call.args[0] for call in invalidate.call_args_list]
        self.assertEqual(labels.count('auto_api.apipublic'), 3)
        self.assertEqual(labels.count('auto_ui.uipublic'), 3)
