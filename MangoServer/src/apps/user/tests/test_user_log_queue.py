import json
import os
import select
import signal
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Thread, get_ident
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch

from django.db import connections
from django.db.backends.sqlite3.base import DatabaseWrapper
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.test.utils import CaptureQueriesContext

from src.apps.user.middleware.user_logs import UserLogsMiddleWare
from src.apps.user.services.audit import user_logs
from src.apps.user.services.audit.user_logs import UserLogService, _UserLogDispatcher


class UserLogQueueTests(SimpleTestCase):
    def test_content_search_keyword_is_not_copied_into_operation_logs(self):
        middleware = UserLogsMiddleWare(lambda request: None)
        for path in middleware.CONTENT_SEARCH_PATHS:
            with self.subTest(path=path):
                payload = {'keyword': 'example-business-value', 'project_product_id': 2}
                request = SimpleNamespace(method='POST', path=path)
                response = SimpleNamespace(renderer_context={'request': SimpleNamespace(data=payload)})
                captured = middleware._capture_request_data(request, response)
                self.assertEqual(captured['keyword'], '***')
                self.assertEqual(captured['project_product_id'], 2)
                self.assertEqual(payload['keyword'], 'example-business-value')

    def setUp(self):
        cleanup = patch.object(user_logs, 'close_old_connections')
        self.connections = cleanup.start()
        self.addCleanup(cleanup.stop)
        self.real_record_batch = UserLogService.record_batch
        record = patch.object(UserLogService, 'record_batch', return_value=1)
        self.record = record.start()
        self.addCleanup(record.stop)

    def dispatcher(self, capacity=5000, batch_size=1, flush_interval=0.05):
        dispatcher = _UserLogDispatcher(capacity=capacity, batch_size=batch_size, flush_interval=flush_interval)
        self.addCleanup(dispatcher.shutdown)
        return dispatcher

    def test_concurrent_submissions_share_one_consumer_and_drain_on_shutdown(self):
        dispatcher = self.dispatcher()
        saved = []
        self.record.side_effect = lambda payloads: saved.extend((payload['id'], get_ident()) for payload in payloads) or 1
        with patch.object(user_logs, 'Thread', wraps=Thread) as thread:
            with ThreadPoolExecutor(max_workers=8) as callers:
                list(callers.map(lambda value: dispatcher.submit({'id': value, 'user': None}), range(40)))
            dispatcher.shutdown(timeout=2)
        thread.assert_called_once()
        self.assertEqual(sorted(value[0] for value in saved), list(range(40)))
        self.assertEqual(len({value[1] for value in saved}), 1)
        self.assertNotEqual(saved[0][1], get_ident())
        self.assertEqual(dispatcher.queue.unfinished_tasks, 0)
        self.assertFalse(dispatcher._worker.is_alive())

    def test_production_capacity_and_batch_settings(self):
        dispatcher = _UserLogDispatcher()
        self.addCleanup(dispatcher.shutdown)
        self.assertEqual(dispatcher.queue.maxsize, 5000)
        self.assertEqual(dispatcher.batch_size, 100)
        self.assertEqual(dispatcher.flush_interval, 1)

    def test_one_hundred_entries_flush_without_waiting_for_interval(self):
        dispatcher = self.dispatcher(batch_size=100, flush_interval=5)
        saved = Event()
        self.record.side_effect = lambda payloads: saved.set() or len(payloads)
        for index in range(99):
            dispatcher.submit({'id': index, 'user': None})
        self.assertFalse(saved.wait(timeout=0.03))
        dispatcher.submit({'id': 99, 'user': None})
        self.assertTrue(saved.wait(timeout=1))
        self.assertEqual(len(self.record.call_args.args[0]), 100)

    def test_interval_flushes_a_partial_batch_and_shutdown_flushes_the_tail(self):
        dispatcher = self.dispatcher(batch_size=100, flush_interval=0.1)
        saved = Event()
        self.record.side_effect = lambda payloads: saved.set() or len(payloads)
        dispatcher.submit({'id': 1, 'user': None})
        self.assertFalse(saved.wait(timeout=0.02))
        self.assertTrue(saved.wait(timeout=1))
        self.assertEqual(len(self.record.call_args.args[0]), 1)
        dispatcher.submit({'id': 2, 'user': None})
        dispatcher.shutdown(timeout=1)
        self.assertEqual(self.record.call_count, 2)
        self.assertEqual(dispatcher.queue.unfinished_tasks, 0)

    def test_drop_warnings_are_rate_limited_and_counts_are_accumulated(self):
        dispatcher = self.dispatcher()
        dispatcher.shutdown()
        with patch.object(user_logs, 'monotonic', side_effect=[100, 120, 161]), \
                self.assertLogs(user_logs.logger, level='WARNING') as messages:
            for index in range(3):
                dispatcher.submit({'id': index})
        self.assertEqual(dispatcher.dropped_count, 3)
        self.assertEqual(len(messages.output), 2)
        self.assertIn('丢弃新日志 2 条', messages.output[-1])

    def test_record_batch_keeps_validation_and_uses_one_bulk_write(self):
        payloads = [{'user': 7, 'method': 'GET', 'status_code': 200, 'url': '/api/example'} for _ in range(100)]
        with patch.object(user_logs, 'validate_model') as validate, \
                patch.object(user_logs.UserLogs.objects, 'bulk_create') as write:
            self.assertEqual(self.real_record_batch(payloads), 100)
        self.assertEqual(validate.call_count, 100)
        write.assert_called_once()
        records = write.call_args.args[0]
        self.assertEqual(len(records), 100)
        self.assertEqual(records[0].user_id, 7)
        self.assertEqual(records[0].method, 'GET')
        self.assertEqual(write.call_args.kwargs['batch_size'], 100)

    def test_full_queue_drops_new_entries_without_synchronous_database_work(self):
        dispatcher = self.dispatcher(capacity=1)
        entered, release = Event(), Event()
        saved = []

        def save(payloads):
            payload = payloads[0]
            if payload['id'] == 1:
                entered.set()
                release.wait(timeout=3)
            saved.append((payload['id'], get_ident()))
            return object()

        self.record.side_effect = save
        try:
            dispatcher.submit({'id': 1, 'user': None})
            self.assertTrue(entered.wait(timeout=2))
            dispatcher.submit({'id': 2, 'user': None})
            with self.assertLogs(user_logs.logger, level='WARNING'):
                dispatcher.submit({'id': 3, 'user': None})
            self.assertNotIn((3, get_ident()), saved)
            self.assertEqual(dispatcher.dropped_count, 1)
        finally:
            release.set()
            dispatcher.shutdown(timeout=2)
        self.assertEqual(sorted(value[0] for value in saved), [1, 2])
        self.assertNotIn(get_ident(), {value[1] for value in saved})

    def test_save_error_does_not_kill_the_worker_or_expose_exception_content(self):
        dispatcher = self.dispatcher()
        self.record.side_effect = [RuntimeError('example-secret-must-not-be-logged'), object()]
        with self.assertLogs(user_logs.logger, level='ERROR') as messages:
            dispatcher.submit({'id': 1, 'user': None})
            dispatcher.submit({'id': 2, 'user': None})
            dispatcher.shutdown(timeout=2)
        self.assertEqual(self.record.call_count, 2)
        self.assertEqual(dispatcher.queue.unfinished_tasks, 0)
        self.assertIn('RuntimeError', ' '.join(messages.output))
        self.assertNotIn('example-secret', ' '.join(messages.output))
        self.assertEqual(self.connections.call_count, 4)

    def test_validation_failure_is_reported(self):
        from src.common.database import ModelMutationValidationError
        with patch.object(user_logs, 'validate_model', side_effect=ModelMutationValidationError({'user': ['invalid']})), \
                patch.object(user_logs.UserLogs.objects, 'bulk_create') as write, \
                self.assertLogs(user_logs.logger, level='ERROR') as messages:
            self.assertEqual(self.real_record_batch([{'user': None}]), 0)
        write.assert_not_called()
        self.assertIn('校验未通过', ' '.join(messages.output))

    def test_anonymous_log_passes_real_validation_without_user_lookup(self):
        payload = {'user': None, 'method': 'GET', 'url': '/api/example', 'status_code': 200}
        with patch.object(user_logs.UserLogs.objects, 'bulk_create') as write, \
                self.assertNoLogs(user_logs.logger, level='ERROR'):
            self.assertEqual(self.real_record_batch([payload]), 1)
        self.assertIsNone(write.call_args.args[0][0].user_id)
        self.assertTrue(user_logs.UserLogs._meta.get_field('user').blank)

    def test_validation_logs_field_reason_and_count_without_payload(self):
        secret = 'example-sensitive-marker'
        bad = {'user': None, 'url': secret * 30, 'request_data': secret, 'response_data': secret}
        good = {'user': None, 'url': '/api/example'}
        with patch.object(user_logs.UserLogs.objects, 'bulk_create') as write, \
                self.assertLogs(user_logs.logger, level='ERROR') as messages:
            self.assertEqual(self.real_record_batch([bad, bad, good]), 1)
        output = ' '.join(messages.output)
        self.assertEqual(len(messages.output), 1)
        self.assertIn("'field': 'url'", output)
        self.assertIn('长度超过上限（256 字符）', output)
        self.assertIn("'count': 2", output)
        self.assertNotIn(secret, output)
        self.assertEqual(len(write.call_args.args[0]), 1)

    def test_unknown_fields_and_raw_validator_messages_are_not_logged(self):
        from django.core.exceptions import ValidationError
        from src.common.database import ModelMutationValidationError
        secret = 'example-sensitive-marker'
        error = ModelMutationValidationError({'user': [secret], secret: [secret]})
        try:
            raise error from ValidationError({'user': ValidationError(secret, code=secret, params={'value': secret})})
        except ModelMutationValidationError:
            pass
        with patch.object(user_logs, 'validate_model', side_effect=error), \
                patch.object(user_logs.UserLogs.objects, 'bulk_create') as write, \
                self.assertLogs(user_logs.logger, level='ERROR') as messages:
            self.assertEqual(self.real_record_batch([{'user': None}]), 0)
        output = ' '.join(messages.output)
        self.assertIn("'field': 'user'", output)
        self.assertIn('<未知字段>', output)
        self.assertIn('未输出原始文案', output)
        self.assertNotIn(secret, output)
        write.assert_not_called()

    def test_single_record_validation_failure_uses_safe_details(self):
        # setUp 只替换批量入口，单条入口仍执行真实字段校验。
        with self.assertLogs(user_logs.logger, level='ERROR') as messages:
            self.assertIsNone(UserLogService.record({'user': None, 'url': 'example-secret' * 30}))
        output = ' '.join(messages.output)
        self.assertIn("'field': 'url'", output)
        self.assertIn('长度超过上限', output)
        self.assertNotIn('example-secret', output)

    def test_connection_cleanup_failure_does_not_stop_consumption(self):
        dispatcher = self.dispatcher()
        self.connections.side_effect = [None, RuntimeError('example-secret'), None, None]
        with self.assertLogs(user_logs.logger, level='ERROR') as messages:
            dispatcher.submit({'id': 1, 'user': None})
            dispatcher.submit({'id': 2, 'user': None})
            dispatcher.shutdown(timeout=2)
        self.assertEqual(self.record.call_count, 2)
        self.assertIn('连接清理失败', ' '.join(messages.output))
        self.assertNotIn('example-secret', ' '.join(messages.output))

    def test_thread_start_failure_drops_instead_of_blocking_the_request(self):
        dispatcher = self.dispatcher()
        with patch.object(user_logs, 'Thread') as thread, self.assertLogs(user_logs.logger, level='WARNING'):
            thread.return_value.start.side_effect = RuntimeError('cannot start thread')
            dispatcher.submit({'id': 1, 'user': None})
        self.record.assert_not_called()
        self.assertEqual(dispatcher.dropped_count, 1)
        self.assertIsNone(dispatcher._worker)

    def test_submissions_after_shutdown_are_dropped_without_database_work(self):
        dispatcher = self.dispatcher()
        dispatcher.shutdown()
        with patch.object(user_logs, 'Thread') as thread, self.assertLogs(user_logs.logger, level='WARNING'):
            dispatcher.submit({'id': 1, 'user': None})
        thread.assert_not_called()
        self.record.assert_not_called()
        self.assertEqual(dispatcher.dropped_count, 1)

    def test_shutdown_timeout_reports_unfinished_count(self):
        dispatcher = self.dispatcher()
        entered, release = Event(), Event()

        def save(payload):
            entered.set()
            release.wait(timeout=3)
            return object()

        self.record.side_effect = save
        try:
            dispatcher.submit({'user': None})
            self.assertTrue(entered.wait(timeout=2))
            with self.assertLogs(user_logs.logger, level='WARNING') as messages:
                dispatcher.shutdown(timeout=0.001)
            self.assertIn('1 条', ' '.join(messages.output))
        finally:
            release.set()
            dispatcher.shutdown(timeout=2)

    def test_login_user_resolution_and_deleted_user_handling_stay_in_writer(self):
        payload = {'user': None, 'request_data': '{}'}
        with patch.object(user_logs.User._default_manager, 'get', return_value=SimpleNamespace(id=9)) as lookup, \
                patch.object(user_logs.User.objects, 'filter') as users:
            users.return_value.exists.return_value = True
            _UserLogDispatcher._persist_batch([(payload, 'reader@example.com')])
            lookup.assert_called_once_with(username='reader@example.com')
            self.assertEqual(self.record.call_args.args[0][0]['user'], 9)
            users.return_value.exists.return_value = False
            _UserLogDispatcher._persist_batch([({'user': 9}, None)])
            self.assertIsNone(self.record.call_args.args[0][0]['user'])
        self.assertIsNone(payload['user'])

    def test_missing_login_user_still_records_anonymous_log(self):
        with patch.object(user_logs.User._default_manager, 'get', side_effect=user_logs.User.DoesNotExist):
            _UserLogDispatcher._persist_batch([({'user': None}, 'reader@example.com')])
        self.record.assert_called_once_with([{'user': None}])

    @skipUnless(hasattr(os, 'register_at_fork'), 'requires fork support')
    def test_fork_rebuilds_queue_and_lock_without_replaying_parent_entries(self):
        original = user_logs._dispatcher
        parent = _UserLogDispatcher(capacity=1)
        parent.queue.put_nowait(({'id': 1}, None))
        parent._lock.acquire()
        user_logs._dispatcher = parent
        reader, writer = os.pipe()
        pid = os.fork()
        if pid == 0:
            try:
                os.close(reader)
                child = user_logs._dispatcher
                fresh = child is not parent and child.queue.empty()
                child.submit({'id': 2, 'user': None})
                child.shutdown(timeout=1)
                result = {'fresh': fresh, 'saved': self.record.call_args.args[0][0]['id'],
                          'calls': self.record.call_count, 'unfinished': child.queue.unfinished_tasks}
                os.write(writer, json.dumps(result).encode())
            finally:
                os._exit(0)
        try:
            os.close(writer)
            ready, _, _ = select.select([reader], [], [], 3)
            if not ready:
                os.kill(pid, signal.SIGKILL)
                self.fail('fork 子进程未能启动独立日志消费者')
            result = json.loads(os.read(reader, 4096))
            self.assertEqual(result, {'fresh': True, 'saved': 2, 'calls': 1, 'unfinished': 0})
            self.assertEqual(parent.queue.qsize(), 1)
            self.record.assert_not_called()
        finally:
            os.close(reader)
            os.waitpid(pid, 0)
            user_logs._dispatcher = original
            parent._lock.release()


class UserLogSnapshotTests(SimpleTestCase):
    def test_request_submits_only_a_redacted_plain_snapshot_without_database_work(self):
        request = RequestFactory().post('/api/example', HTTP_SOURCE_TYPE='1')
        request.user = {'id': 7}
        body = {'username': 'reader@example.com', 'password': 'example-secret',
                'nested': {'Authorization': 'example-token'}}
        response = SimpleNamespace(status_code=200, data={'code': 200, 'msg': 'ok', 'data': {'token': 'example-token'}},
                                   renderer_context={'request': SimpleNamespace(data=body)})
        middleware = UserLogsMiddleWare(lambda value: response)
        with patch.object(UserLogService, 'submit') as submit:
            self.assertIs(middleware.process_response(request, response), response)
        entry = submit.call_args.args[0]
        self.assertEqual(entry['user'], 7)
        self.assertIsNone(submit.call_args.kwargs['username'])
        self.assertEqual(json.loads(entry['request_data'])['password'], '***')
        self.assertNotIn('example-secret', json.dumps(entry))
        self.assertNotIn('example-token', json.dumps(entry))
        self.assertTrue(all(isinstance(value, (str, int, type(None))) for value in entry.values()))
        body['username'] = 'changed@example.com'
        self.assertIn('reader@example.com', entry['request_data'])

    def test_bad_snapshot_does_not_break_the_response_or_log_sensitive_error_text(self):
        middleware = UserLogsMiddleWare(lambda value: None)
        response = SimpleNamespace(status_code=200)
        with patch.object(middleware, '_build_log_entry', side_effect=RuntimeError('example-secret')), \
                patch.object(UserLogService, 'submit') as submit, \
                self.assertLogs('src.apps.user.middleware.user_logs', level='ERROR') as messages:
            self.assertIs(middleware.process_response(RequestFactory().get('/api/example'), response), response)
        submit.assert_not_called()
        self.assertNotIn('example-secret', ' '.join(messages.output))


class _LogStorageTestRouter:
    def db_for_read(self, model, **hints):
        return 'log_batch_test' if model in (user_logs.User, user_logs.UserLogs) else None

    db_for_write = db_for_read


class UserLogBatchStorageTests(SimpleTestCase):
    def test_batch_inserts_once_and_preserves_validation_and_field_conversion(self):
        alias = 'log_batch_test'
        database = DatabaseWrapper({
            'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:', 'USER': '', 'PASSWORD': '',
            'HOST': '', 'PORT': '', 'OPTIONS': {}, 'TIME_ZONE': None, 'AUTOCOMMIT': True,
            'CONN_MAX_AGE': 0, 'CONN_HEALTH_CHECKS': False, 'ATOMIC_REQUESTS': False,
        }, alias=alias)
        database.ensure_connection()
        connections[alias] = database
        try:
            # 独立内存表和定向路由，不连接环境库、不运行迁移。
            with database.cursor() as cursor:
                for model in (user_logs.User, user_logs.UserLogs):
                    columns = ', '.join(f'"{field.column}" {field.db_type(database)}'
                                        + (' PRIMARY KEY' if field.primary_key else '')
                                        for field in model._meta.concrete_fields)
                    cursor.execute(f'CREATE TABLE "{model._meta.db_table}" ({columns})')
            with override_settings(DATABASE_ROUTERS=[_LogStorageTestRouter()]):
                user_logs.User.objects.bulk_create([
                    user_logs.User(id=1, name='示例用户', username='reader@example.com'),
                ])
                payload = {'user': 1, 'source_type': 1, 'ip': '127.0.0.1', 'url': '/api/example',
                           'method': 'GET', 'status_code': 200, 'request_data': '{}', 'response_data': '{}'}
                expected = UserLogService.record(payload)
                self.assertIsNotNone(expected)
                with CaptureQueriesContext(database) as queries:
                    self.assertEqual(UserLogService.record_batch([dict(payload) for _ in range(100)]), 100)
                inserts = [query['sql'] for query in queries if query['sql'].lstrip().upper().startswith('INSERT')]
                self.assertEqual(len(inserts), 1)
                actual = user_logs.UserLogs.objects.exclude(pk=expected.pk).first()
                self.assertIsNotNone(actual.create_time)
                for field in ('user_id', 'source_type', 'ip', 'url', 'method', 'status_code', 'request_data', 'response_data'):
                    self.assertEqual(getattr(actual, field), getattr(expected, field))
                with self.assertLogs(user_logs.logger, level='ERROR'):
                    self.assertEqual(UserLogService.record_batch([{**payload, 'url': 'x' * 300}, payload]), 1)
                self.assertEqual(user_logs.UserLogs.objects.count(), 102)
                anonymous = {**payload, 'user': None}
                saved = UserLogService.record(anonymous)
                self.assertIsNotNone(saved)
                self.assertIsNone(saved.user_id)
                self.assertEqual(UserLogService.record_batch([anonymous]), 1)
                self.assertEqual(user_logs.UserLogs.objects.filter(user__isnull=True).count(), 2)
        finally:
            del connections[alias]
            database.connection.close()
