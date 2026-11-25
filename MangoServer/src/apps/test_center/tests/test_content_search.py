import io
import gzip
import json
import time
from contextlib import nullcontext
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from pydantic import ValidationError

from src.apps.test_center.schemas.content_search import ContentSearchQuery, ContentSearchTask
from src.apps.test_center.services.results.content_search import ExecutionContentSearchService as Search
from src.apps.test_center.selectors.execution_result import ExecutionResultAccessSelector as Results
from src.apps.data_factory.selectors.execution_audit import ExecutionAuditSelector as Audits
from src.apps.test_center.exceptions import TestCenterError, EXECUTION_SEARCH_DENIED
from src.apps.user.services.authorization.permission import ProjectProductScopeService


class ContentSearchTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id=7)
        self.payload = dict(project_product_id=2, test_env=0, day=timezone.now().date().isoformat(), keyword='AUTO_TEMPLATE')
        now = time.time()
        self.task = ContentSearchTask(task_id='a' * 32, owner_id=7, kind='automation',
            query=ContentSearchQuery.model_validate(self.payload), started_at=now, updated_at=now)
        self.store = Mock()
        self.store.get_many.return_value = {'active': {'task_id': self.task.task_id}}
        self.store.set_if_absent.return_value = (True, 'lease-version')
        slot = patch.object(Search, '_slot', Mock())
        slot.start(); self.addCleanup(slot.stop)
        for target, replacement in ((Search, 'store'), (Search, 'authorize')):
            mock = patch.object(target, replacement, return_value=self.store if replacement == 'store' else None)
            mock.start(); self.addCleanup(mock.stop)

    def row(self, **values):
        defaults = dict(id=1, create_time=timezone.now(), result_size=30, result_object_key='results/example.json',
            result_cleaned=False, target_type='api_case', target_id=9, test_suite_id=22,
            test_suite_detail=None, trigger_user=SimpleNamespace(name='测试用户'), source_type='report')
        defaults.update(values)
        return SimpleNamespace(**defaults)

    def run_task(self, rows, **patches):
        with patch.object(Results, 'search_batch', side_effect=[rows, []]), \
                patch('src.apps.test_center.services.results.content_search.UserQuerySelector.user') as users, \
                (patch.multiple(Search, **patches) if patches else nullcontext()):
            users.return_value.select_related.return_value.get.return_value = self.user
            Search.run(self.task, 'lease-version')

    def test_requires_single_recent_date_and_keyword(self):
        for field in ('day', 'keyword'):
            invalid = dict(self.payload); invalid.pop(field)
            with self.subTest(field=field), self.assertRaises(ValidationError):
                ContentSearchQuery.model_validate(invalid)
        for values in ({'day': (timezone.now().date() - timedelta(days=30)).isoformat()},
                       {'day': (timezone.now().date() + timedelta(days=1)).isoformat()},
                       {'day': '2026-01-01,2026-01-02'}, {'keyword': ' '}, {'keyword': 'x' * 201},
                       {'project_product_id': True}, {'test_env': 999}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                ContentSearchQuery.model_validate({**self.payload, **values})

    def test_product_and_environment_may_be_omitted_or_null(self):
        for fields in ({}, {'project_product_id': None, 'test_env': None}, {'test_env': 0}, {'project_product_id': 2}):
            query = ContentSearchQuery.model_validate({'day': self.payload['day'], 'keyword': 'example', **fields})
            self.assertEqual(query.project_product_id, fields.get('project_product_id'))
            self.assertEqual(query.test_env, fields.get('test_env'))

    def test_start_freezes_authorized_product_scope_for_optional_search(self):
        payload = {'day': self.payload['day'], 'keyword': 'example'}
        with patch.object(Search, 'authorize', return_value=[2, 3]), patch.object(Search._executor, 'submit') as submit:
            result = Search.start(self.user, 'automation', payload)
        task = submit.call_args.args[1]
        self.assertEqual(task.product_scope, [2, 3])
        self.assertNotIn('product_scope', result)

    def test_previous_29_days_and_natural_day_bounds(self):
        for days in (0, 1, 29):
            query = ContentSearchQuery.model_validate({**self.payload,
                'day': (timezone.now().date() - timedelta(days=days)).isoformat()})
            self.task.query = query
            start, end = Search.bounds(self.task)
            self.assertEqual(start.hour, 0)
            self.assertLessEqual(end - start, timedelta(days=1))
            self.assertEqual(start.date(), query.day)

    @override_settings(USE_TZ=True, TIME_ZONE='Asia/Shanghai')
    def test_aware_natural_day(self):
        start, end = Search.bounds(self.task)
        self.assertTrue(timezone.is_aware(start))
        self.assertTrue(timezone.is_aware(end))

    def test_global_atomic_lease_prevents_second_job(self):
        self.store.set_if_absent.return_value = (False, None)
        with patch.object(Search._executor, 'submit') as submit, self.assertRaises(TestCenterError):
            Search.start(self.user, 'automation', self.payload)
        submit.assert_not_called()

    def test_blocked_local_reader_does_not_build_an_executor_queue(self):
        Search._slot.acquire.return_value = False
        with patch.object(Search._executor, 'submit') as submit, self.assertRaises(TestCenterError):
            Search.start(self.user, 'automation', self.payload)
        submit.assert_not_called()
        self.store.delete_if_version.assert_called_once_with('active', 'lease-version')

    def test_start_saves_query_only_in_runtime_namespace(self):
        with patch.object(Search._executor, 'submit') as submit:
            result = Search.start(self.user, 'automation', self.payload)
        submit.assert_called_once()
        self.assertEqual(result['query']['project_product_id'], 2)
        self.store.set.assert_called_once()

    def test_start_response_is_not_mutated_by_immediate_worker_progress(self):
        def submit(_, task, lease_version):
            task.match_count = 1
        with patch.object(Search._executor, 'submit', side_effect=submit):
            response = Search.start(self.user, 'automation', self.payload)
        self.assertEqual(response['count'], 0)
        self.assertEqual(response['status'], 'running')

    def test_no_fallback_on_missing_runtime_table(self):
        self.store.set_if_absent.side_effect = RuntimeError('storage not ready')
        with patch.object(Search._executor, 'submit') as submit, self.assertRaises(RuntimeError):
            Search.start(self.user, 'automation', self.payload)
        submit.assert_not_called()

    def test_scans_actual_object_file_and_preserves_evidence_location(self):
        payload = {'steps': [{'request': {'json': {'name': 'AUTO_TEMPLATE_001'}}, 'response': {'id': 123}}]}
        with patch('src.apps.test_center.services.results.content_search.default_storage.open',
                   return_value=io.BytesIO(json.dumps(payload).encode())) as opened:
            self.run_task([self.row()])
        opened.assert_called_once_with('results/example.json', 'rb')
        self.assertEqual(self.task.status, 'completed')
        self.assertEqual(self.task.items[0].record_id, 1)
        self.assertEqual(self.task.items[0].path, 'steps[0].request.json.name')
        self.assertEqual(self.task.items[0].target_id, 9)

    def test_reads_inline_json_when_no_object_file(self):
        with patch.object(Results, 'inline_search_payload', return_value='{"response":"AUTO_TEMPLATE"}'):
            payload, _, incomplete = Search.payload(self.task, self.row(result_object_key=None))
        self.assertEqual(payload, {'response': 'AUTO_TEMPLATE'})
        self.assertFalse(incomplete)

    def test_gzip_search_reads_original_json_and_counts_decoded_bytes(self):
        raw = json.dumps({'response': 'AUTO_TEMPLATE' * 100}).encode()
        compressed = gzip.compress(raw)
        with patch('src.apps.test_center.services.results.content_search.default_storage.open',
                   return_value=io.BytesIO(compressed)):
            payload, size, incomplete = Search.payload(self.task, self.row(
                result_object_key='results/example.json.gz', result_size=len(compressed)))
        self.assertEqual(payload, json.loads(raw))
        self.assertEqual(size, len(raw))
        self.assertFalse(incomplete)

    def test_small_compressed_file_cannot_bypass_uncompressed_search_budget(self):
        compressed = gzip.compress(json.dumps({'response': 'AUTO_TEMPLATE' * 1000}).encode())
        with patch.object(Search, 'MAX_FILE_BYTES', 1000), patch(
            'src.apps.test_center.services.results.content_search.default_storage.open',
            return_value=io.BytesIO(compressed)):
            payload, size, incomplete = Search.payload(self.task, self.row(result_size=len(compressed)))
        self.assertIsNone(payload)
        self.assertTrue(incomplete)
        self.assertEqual(size, 1001)

    def test_actual_limits_allow_nine_mib_plain_and_gzip_results(self):
        self.assertEqual(Search.MAX_FILE_BYTES, 20 * 1024 * 1024)
        raw = json.dumps({'name': 'AUTO_TEMPLATE', 'padding': 'x' * (9 * 1024 * 1024)}).encode()
        for stored in (raw, gzip.compress(raw)):
            with self.subTest(compressed=stored is not raw), patch(
                    'src.apps.test_center.services.results.content_search.default_storage.open',
                    return_value=io.BytesIO(stored)):
                self.task.read_bytes = 0
                payload, size, incomplete = Search.payload(self.task, self.row(result_size=len(stored)))
                self.assertFalse(incomplete)
                self.assertEqual(size, len(raw))
                self.assertIsNotNone(Search.match(payload, 'AUTO_TEMPLATE')[0])

    def test_gzip_over_twenty_mib_is_still_incomplete(self):
        raw = json.dumps({'padding': 'x' * Search.MAX_FILE_BYTES}).encode()
        stored = gzip.compress(raw)
        with patch('src.apps.test_center.services.results.content_search.default_storage.open',
                   return_value=io.BytesIO(stored)):
            payload, size, incomplete = Search.payload(self.task, self.row(result_size=len(stored)))
        self.assertIsNone(payload)
        self.assertTrue(incomplete)
        self.assertEqual(size, Search.MAX_FILE_BYTES + 1)

    def test_exact_twenty_mib_result_is_allowed(self):
        prefix, suffix = b'{"name":"AUTO_TEMPLATE","padding":"', b'"}'
        raw = prefix + b'x' * (Search.MAX_FILE_BYTES - len(prefix) - len(suffix)) + suffix
        with patch('src.apps.test_center.services.results.content_search.default_storage.open',
                   return_value=io.BytesIO(gzip.compress(raw))):
            payload, size, incomplete = Search.payload(self.task, self.row(result_size=1000))
        self.assertEqual(size, Search.MAX_FILE_BYTES)
        self.assertFalse(incomplete)
        self.assertEqual(payload['name'], 'AUTO_TEMPLATE')

    def test_large_cumulative_read_does_not_limit_next_file(self):
        self.task.read_bytes = 100 * 1024 * 1024
        stored = gzip.compress(json.dumps({'padding': 'x' * (2 * 1024 * 1024)}).encode())
        with patch('src.apps.test_center.services.results.content_search.default_storage.open',
                   return_value=io.BytesIO(stored)):
            payload, size, incomplete = Search.payload(self.task, self.row(result_size=len(stored)))
        self.assertIsNotNone(payload)
        self.assertFalse(incomplete)
        self.assertGreater(size, 2 * 1024 * 1024)
        self.assertGreater(self.task.read_bytes, 102 * 1024 * 1024)

    def test_gzip_object_file_uses_the_same_bounded_search(self):
        import gzip
        content = json.dumps({'response': 'AUTO_TEMPLATE'}).encode()
        with patch('src.apps.test_center.services.results.content_search.default_storage.open',
                   return_value=io.BytesIO(gzip.compress(content))):
            self.run_task([self.row(result_object_key='results/example.json.gz')])
        self.assertEqual(len(self.task.items), 1)
        self.assertEqual(self.task.read_bytes, len(content))

    def test_corrupt_file_still_consumes_read_budget(self):
        with patch('src.apps.test_center.services.results.content_search.default_storage.open',
                   return_value=io.BytesIO(b'not-json')):
            with self.assertRaises(ValueError):
                Search.payload(self.task, self.row())
        self.assertEqual(self.task.read_bytes, len(b'not-json'))

    def test_oversized_inline_json_still_consumes_read_budget(self):
        raw = '"' + 'x' * 100 + '"'
        with patch.object(Results, 'inline_search_payload', return_value=raw), patch.object(Search, 'MAX_FILE_BYTES', 30):
            payload, size, incomplete = Search.payload(self.task, self.row(result_object_key=None))
        self.assertIsNone(payload)
        self.assertEqual(size, self.task.read_bytes)
        self.assertTrue(incomplete)

    def test_corrupt_missing_cleaned_and_oversized_are_not_reported_as_no_hit(self):
        for row, file in ((self.row(), io.BytesIO(b'not json')),
                          (self.row(result_cleaned=True), io.BytesIO(b'')),
                          (self.row(result_size=Search.MAX_FILE_BYTES + 1), io.BytesIO(b''))):
            with self.subTest(row=row), patch('src.apps.test_center.services.results.content_search.default_storage.open', return_value=file):
                self.task.scanned = self.task.skipped = 0
                self.task.status = 'running'
                self.run_task([row])
                self.assertEqual(self.task.status, 'partial')
                self.assertEqual(self.task.skipped, 1)

    def test_cancel_does_not_read_next_file_and_releases_only_owned_lease(self):
        self.store.get_many.return_value = {'active': {'task_id': self.task.task_id}, f'cancel:{self.task.task_id}': True}
        reader = Mock()
        self.run_task([self.row()], payload=reader)
        reader.assert_not_called()
        self.assertEqual(self.task.status, 'cancelled')
        self.store.delete_if_version.assert_called_once_with('active', 'lease-version')

    def test_lost_lease_does_not_read_next_file(self):
        self.store.get_many.return_value = {'active': {'task_id': 'another-job'}}
        reader = Mock()
        self.run_task([self.row()], payload=reader)
        reader.assert_not_called()
        self.assertEqual(self.task.status, 'partial')

    def test_scans_beyond_old_limits_and_persists_unlimited_hits_in_bounded_pages(self):
        cache = {}
        self.store.set.side_effect = lambda key, value, ttl: cache.update({key: value})
        self.store.get.side_effect = lambda key: cache.get(key)
        self.store.compare_and_set.return_value = (True, 'renewed-version')
        def read(task, row):
            task.read_bytes += 1024 * 1024
            return {'name': 'AUTO_TEMPLATE'}, 1024 * 1024, False
        import itertools
        clock = itertools.count()
        with patch('src.apps.test_center.services.results.content_search.time.monotonic', side_effect=lambda: next(clock)):
            self.run_task([self.row(id=index) for index in range(1, 3102)], payload=Mock(side_effect=read))
        self.assertEqual(self.task.status, 'completed')
        self.assertEqual(self.task.scanned, 3101)
        self.assertEqual(self.task.match_count, 3101)
        self.assertLess(len(self.task.items), 20)
        self.assertGreater(self.task.read_bytes, 64 * 1024 * 1024)
        self.store.compare_and_set.assert_called()
        pages = [value['items'] for key, value in cache.items() if key.startswith('hits:')]
        self.assertTrue(all(len(items) <= 20 for items in pages))
        self.assertEqual(sum(len(items) for items in pages), 3101)
        with patch.object(Results, 'search_names', return_value={}):
            page = Search.present(self.task, 6)
        self.assertEqual(page['count'], 3101)
        self.assertEqual(page['items'][0]['record_id'], 101)

    def test_previous_payload_is_released_before_reading_next_record(self):
        import weakref
        class Payload(dict):
            pass
        previous = []
        def read(task, row):
            if previous:
                self.assertIsNone(previous[-1]())
            payload = Payload(name='AUTO_TEMPLATE')
            previous.append(weakref.ref(payload))
            return payload, 50, False
        self.run_task([self.row(id=index) for index in range(25)], payload=Mock(side_effect=read))
        self.assertEqual(self.task.match_count, 25)
        self.assertTrue(all(reference() is None for reference in previous))

    def test_cached_page_cannot_publish_hits_ahead_of_saved_progress(self):
        from src.apps.test_center.schemas.content_search import ContentSearchHit
        hit = ContentSearchHit(record_id=1, target_type='api_case', create_time='2026-11-19', path='name', snippet='example')
        self.task.match_count = 1
        self.store.get.return_value = {'items': [hit.model_dump()] * 20}
        with patch.object(Results, 'search_names', return_value={}):
            response = Search.present(self.task, 1)
        self.assertEqual(response['count'], 1)
        self.assertEqual(len(response['items']), 1)

    def test_expired_hit_page_does_not_stop_running_task(self):
        self.task.match_count = 20
        self.store.get.return_value = None
        response = Search.present(self.task, 1)
        self.assertEqual(response['status'], 'running')
        self.assertIn('过期', response['message'])
        self.assertEqual(response['items'], [])

    def test_slow_batch_is_still_running_when_lease_is_alive(self):
        self.task.updated_at = time.time() - 181
        raw = self.task.model_dump(mode='json')
        self.store.get.side_effect = lambda key: raw if key.startswith('task:') else {'task_id': self.task.task_id}
        response = Search.get(self.user, 'automation', self.task.task_id)
        self.assertEqual(response['status'], 'running')

    def test_case_insensitive_literal_not_regex_and_json_string_values(self):
        match, _ = Search.match({'body': '{"name":"auto_template[1]"}'}, 'AUTO_TEMPLATE[1]')
        self.assertEqual(match[0], 'body.name')
        self.assertIsNone(Search.match({'name': 'AUTO_TEMPLATE1'}, 'AUTO_TEMPLATE[1]')[0])

    def test_secrets_are_not_searchable_or_returned_in_surrounding_fragment(self):
        for payload in ({'Authorization': 'secret-value'}, {'headers': [{'key': 'Authorization', 'value': 'secret-value'}]},
                        {'body': '{"password":"secret-value"}'}):
            self.assertIsNone(Search.match(payload, 'secret-value')[0])
        match, _ = Search.match({'text': 'password=secret-value name=AUTO_TEMPLATE'}, 'AUTO_TEMPLATE')
        self.assertNotIn('secret-value', match[1])

    def test_large_flat_array_is_searched_lazily_without_node_count_limit(self):
        import tracemalloc
        payload = [0] * 100000 + ['AUTO_TEMPLATE']
        tracemalloc.start()
        try:
            match, incomplete = Search.match(payload, 'AUTO_TEMPLATE')
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertIsNotNone(match)
        self.assertFalse(incomplete)
        self.assertLess(peak, 12 * 1024 * 1024)

    def test_owners_kinds_and_current_product_scope_are_rechecked(self):
        self.store.get.return_value = self.task.model_dump(mode='json')
        for user, kind in ((SimpleNamespace(id=8), 'automation'), (self.user, 'datasource')):
            with self.assertRaises(TestCenterError):
                Search.owned(user, kind, self.task.task_id)
        with patch.object(Search, 'authorize', side_effect=TestCenterError(EXECUTION_SEARCH_DENIED)):
            with self.assertRaises(TestCenterError):
                Search.get(self.user, 'automation', self.task.task_id)

    def test_datasource_fields_and_parameter_case_source(self):
        self.task.kind = 'datasource'
        row = self.row(source_type='api_case_parameter', source_id=99, source_stage='parameter_front',
                       source_detail={'case_id': 9, 'test_suite_id': 22}, search_text='INSERT AUTO_TEMPLATE',
                       search_parameters='{}', search_preview='', result_truncated=False)
        with patch.object(Audits, 'search_batch', side_effect=[[row], []]), \
                patch.object(Audits, 'search_payload', return_value='{"执行内容":"INSERT AUTO_TEMPLATE"}'), \
                patch('src.apps.test_center.services.results.content_search.UserQuerySelector.user'):
            Search.run(self.task, 'lease-version')
        self.assertEqual(self.task.items[0].target_type, 'api_case')
        self.assertEqual(self.task.items[0].target_id, 9)
        self.assertEqual(self.task.items[0].stage, 'parameter_front')


class ContentSearchScopeTests(SimpleTestCase):
    def test_optional_filters_compile_without_null_environment_or_unscoped_product_query(self):
        from django.db.models.query import QuerySet
        statements = []
        def fetch(queryset):
            if queryset._result_cache is None:
                statements.append(str(queryset.query))
                queryset._result_cache = []
        query = ContentSearchQuery(day=timezone.now().date(), keyword='example')
        start = timezone.now() - timedelta(days=1)
        with patch.object(QuerySet, '_fetch_all', fetch):
            Results.search_batch(query, start, timezone.now(), product_ids=[2])
            Audits.search_batch(query, start, timezone.now(), product_ids=[2])
        self.assertEqual(len(statements), 2)
        for statement in statements:
            self.assertIn('project_product_id', statement)
            self.assertIn('IN (2)', statement)
            self.assertNotIn('test_env` IS NULL', statement)
            self.assertNotIn('result_data`', statement.split(' FROM ')[0])

    def test_optional_product_scope_uses_departments_not_global_access(self):
        user = SimpleNamespace(id=7)
        with patch('src.apps.test_center.services.results.content_search.PermissionMenuService.is_effective_super_admin', return_value=False), \
                patch.object(ProjectProductScopeService, 'can_view_all_project_data', return_value=False), \
                patch.object(ProjectProductScopeService, 'project_product_ids_for_user', return_value={2, 3}):
            self.assertEqual(Search.authorize(user, None), [2, 3])

    def test_scope_revocation_denies_existing_optional_search(self):
        now = time.time()
        task = ContentSearchTask(task_id='a' * 32, owner_id=7, kind='automation', product_scope=[2, 3],
            query={'day': timezone.now().date().isoformat(), 'keyword': 'example'}, started_at=now, updated_at=now)
        with patch.object(Search, 'authorize', return_value=[3]):
            with self.assertRaises(TestCenterError):
                Search.authorize_task(SimpleNamespace(id=7), task)
        task.product_scope = None
        with patch.object(Search, 'authorize', return_value=[3]):
            with self.assertRaises(TestCenterError):
                Search.authorize_task(SimpleNamespace(id=7), task)

    def test_product_scope_denial_stops_before_runtime_or_file_access(self):
        with patch.object(ProjectProductScopeService, 'has_project_product', return_value=False), \
                patch.object(Search, 'store') as store:
            with self.assertRaises(TestCenterError):
                Search.start(SimpleNamespace(id=7), 'automation', dict(project_product_id=2,
                    test_env=0, day=timezone.now().date().isoformat(), keyword='example'))
        store.assert_not_called()

    def test_http_routes_have_explicit_read_mapping_for_each_action(self):
        from django.urls import resolve
        from src.apps.user.services.authorization.http_permission_registry import permission_for_view
        for path, page in (('/api/system/execution/result/search', 'system.execution_result'),
                           ('/api/system/sql-execution/search', 'system.sql_execution')):
            for suffix, method, action in (('', 'post', 'search_start'), ('', 'get', 'search_status'),
                                            ('/cancel', 'post', 'search_cancel')):
                match = resolve(path + suffix)
                self.assertEqual(match.func.actions[method], action)
                self.assertEqual(permission_for_view(match.func.cls, action, method, {}), f'{page}:read')
