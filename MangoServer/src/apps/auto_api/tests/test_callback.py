from src.apps.user.services.authorization.http_permission_registry import permission_for_view
"""回调闭环测试只使用独立内存 SQLite，不生成或运行迁移。"""
import hashlib
import json
import unittest
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.db import connections, transaction
from django.db.utils import ConnectionHandler
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.utils import timezone

from src.apps.auto_api.enums.callback import CallbackRunStatus
from src.apps.auto_api.exceptions import AutoApiError, MockRuntimeLookupError
from src.apps.auto_api.models import ApiCase, ApiMockConfig, ApiCaseCallbackRun, ApiMockRequestLog
from src.apps.auto_api.schemas.callback import validate_callback_rules
from src.apps.auto_api.services.callbacks.callback import ApiCallbackService
from src.apps.auto_api.services.callbacks.callback_validation import compact_json, validate_delivery
from src.apps.auto_api.services.callbacks.callback_general import CallbackGeneralAssertionService
from src.common.testing import ObtainTestData
from src.apps.auto_api.services.mock.mock_runtime import MockRuntimeService


def callback_rule():
    return {'key': 'callback', 'name': '事件回调', 'trigger_step_key': 'step-1', 'mock_config_id': 1,
            'correlation': {'source': 'envelope_json', 'field': '$.header.event_id',
                            'expected': {'cache_key': 'callback_run_id'}},
            'checks': [{'key': 'compact', 'type': 'json_compact', 'source': 'raw_body'}]}


def general_assertion(expect, *, method='p_is_equal_to', group='', logic='AND'):
    return {'method': method, 'group_name': group, 'group_logic': logic,
            'value': {'value': method, 'parameter': [
                {'f': 'actual', 'v': 'ignored'}, {'f': 'expect', 'v': expect}]}}


class CallbackGeneralTests(SimpleTestCase):
    def test_shared_engine_uses_typed_callback_value_and_case_cache(self):
        data = ObtainTestData()
        data.set_cache('expected', 200)
        assertions = [general_assertion('${{expected}}')]
        passed, results = CallbackGeneralAssertionService.evaluate(assertions, 200, data)
        self.assertTrue(passed)
        self.assertEqual(assertions[0]['value']['parameter'][0]['v'], 'ignored')
        self.assertTrue(results)
        self.assertNotIn('actual', results[0])
        self.assertNotIn('expect', results[0])
        self.assertFalse(CallbackGeneralAssertionService.evaluate(assertions, 201, data)[0])

    def test_contains_uses_shared_method_and_does_not_log_cache_values(self):
        with patch('src.apps.auto_api.services.execution.base.case_parameter.log.api.debug') as debug:
            passed, _ = CallbackGeneralAssertionService.evaluate(
                [general_assertion('approved', method='p_contains')], 'status-approved', ObtainTestData())
        self.assertTrue(passed)
        debug.assert_not_called()

    def test_or_group_and_independent_and_items_match_general_engine(self):
        data = ObtainTestData()
        group = [general_assertion('wrong', group='either', logic='OR'),
                 general_assertion('right', group='either', logic='OR')]
        passed, results = CallbackGeneralAssertionService.evaluate(group, 'right', data)
        self.assertTrue(passed)
        self.assertTrue(all(item['group_result'] for item in results))
        self.assertFalse(CallbackGeneralAssertionService.evaluate(
            group + [general_assertion('wrong')], 'right', data)[0])

    def test_snapshot_is_encrypted_and_independent_between_deliveries(self):
        data = ObtainTestData()
        data.set_cache('token', 'synthetic-sensitive-value')
        data.set_cache('expected', {'nested': [1]})
        data.set_data_factory_cache('large_id', 9007199254740993)
        frozen = CallbackGeneralAssertionService.freeze(data)
        self.assertNotIn('synthetic-sensitive-value', frozen)
        left = CallbackGeneralAssertionService.restore(frozen)
        right = CallbackGeneralAssertionService.restore(frozen)
        left.set_cache('expected', 2)
        self.assertEqual(right.get_cache('expected'), {'nested': [1]})
        self.assertEqual(data.get_cache('expected'), {'nested': [1]})
        self.assertEqual(right.get_cache('df.large_id'), 9007199254740993)
        with self.assertRaises(AutoApiError):
            CallbackGeneralAssertionService.restore('invalid')

    def test_snapshot_size_is_bounded(self):
        data = ObtainTestData()
        data.set_cache('large', 'a' * (1024 * 1024))
        with self.assertRaises(AutoApiError):
            CallbackGeneralAssertionService.freeze(data)

    def test_general_checks_do_not_leak_values_on_failure(self):
        data = ObtainTestData()
        data.set_cache('expected', 'synthetic-sensitive-value')
        rule = validate_callback_rules([callback_rule()])[0]
        rule['checks'] = [{'key': 'field', 'type': 'field', 'source': 'envelope_json',
                           'field': '$.code', 'assertions': [general_assertion('${{expected}}')]}]
        result, _ = validate_delivery(rule, b'{"code":200}', {}, SimpleNamespace(), {}, test_data=data)
        self.assertFalse(result[0]['passed'])
        self.assertNotIn('synthetic-sensitive-value', json.dumps(result))
        self.assertTrue(result[0]['assertions'])


class CallbackValidationTests(SimpleTestCase):
    def test_compact_json_preserves_strings_and_escapes(self):
        self.assertTrue(compact_json('{"text":"a b\\n\\\"c","id":9007199254740993}'))
        self.assertFalse(compact_json('{\n "text": "a b"\n}'))

    def test_duplicate_keys_and_invalid_numbers_rejected(self):
        for text in ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}']:
            with self.assertRaises(ValueError):
                compact_json(text)

    def test_exact_count_requires_observation(self):
        rule = callback_rule()
        rule['events'] = {'mode': 'exact', 'count': 1}
        with self.assertRaises(AutoApiError):
            validate_callback_rules([rule])

    def test_invalid_and_duplicate_rules_rejected_without_input_leak(self):
        rule = callback_rule()
        for value in [[rule, rule], [dict(rule, timeout_seconds=301)], [dict(rule, checks=[])]]:
            with self.assertRaises(AutoApiError):
                validate_callback_rules(value)
        rule['checks'][0]['type'] = 'secret-not-a-protocol'
        with self.assertRaises(AutoApiError) as error:
            validate_callback_rules([rule])
        self.assertNotIn('secret-not-a-protocol', error.exception.msg)

    def test_pretty_body_signature_passes_but_compact_check_fails(self):
        raw = b'{\n "header": {"event_id":"event-1"}\n}'
        signature = hashlib.sha256(b'123noncekey' + raw).hexdigest()
        rule = validate_callback_rules([callback_rule()])[0]
        rule['checks'].append({'key': 'signature', 'type': 'lark_signature', 'source': 'raw_body'})
        results, _ = validate_delivery(rule, raw, {'X-Lark-Request-Timestamp': '123',
            'X-Lark-Request-Nonce': 'nonce', 'X-Lark-Signature': signature}, SimpleNamespace(), {'encrypt_key': 'key'})
        self.assertFalse(results[0]['passed'])
        self.assertTrue(results[1]['passed'])
        results, _ = validate_delivery(rule, b'{"header":{"event_id":"event-1"}}', {
            'X-Lark-Request-Timestamp': '123', 'X-Lark-Request-Nonce': 'nonce', 'X-Lark-Signature': signature,
        }, SimpleNamespace(), {'encrypt_key': 'key'})
        self.assertFalse(results[1]['passed'])

    def test_customer_compact_signature_is_diagnostic_only(self):
        raw = b'{ "id": 1 }'
        rule = validate_callback_rules([callback_rule()])[0]
        rule['checks'] = [{'key': 'signature', 'type': 'lark_signature', 'source': 'raw_body'},
                          {'key': 'customer', 'type': 'lark_compact_signature_simulation', 'source': 'raw_body'}]
        signature = hashlib.sha256(b'123noncekey' + raw).hexdigest()
        results, _ = validate_delivery(rule, raw, {'X-Lark-Request-Timestamp': '123',
            'X-Lark-Request-Nonce': 'nonce', 'X-Lark-Signature': signature}, SimpleNamespace(), {'encrypt_key': 'key'})
        self.assertTrue(results[0]['passed'])
        self.assertFalse(results[1]['passed'])
        self.assertTrue(results[1]['diagnostic'])

    def test_missing_or_recovery_trigger_fails_before_execution(self):
        rules = [callback_rule()]
        for steps in [[], [SimpleNamespace(id=1, execution_config={'is_recovery': True})]]:
            with self.assertRaises(AutoApiError):
                ApiCallbackService.validate_execution(rules, steps)

    def test_text_callback_can_use_raw_text_and_header_identity(self):
        rule = validate_callback_rules([callback_rule()])[0]
        rule['checks'] = [{'key': 'text', 'type': 'field', 'source': 'raw_body',
                           'operator': 'equals', 'field': '', 'expected': 'callback accepted'}]
        results, body = validate_delivery(rule, b'callback accepted', {}, SimpleNamespace(), {})
        self.assertTrue(all(item['passed'] for item in results))
        self.assertEqual(body, 'callback accepted')


class CallbackTestRouter:
    MODELS = {'apicase', 'apimockconfig', 'apicasecallbackrun', 'apimockrequestlog'}

    def db_for_read(self, model, **hints):
        return 'callback_test' if model._meta.app_label == 'auto_api' and model._meta.model_name in self.MODELS else None

    db_for_write = db_for_read


class CallbackPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        connections.databases['callback_test'] = ConnectionHandler({
            'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'},
        }).databases['default']
        cls.db = connections['callback_test']
        cls.db.disable_constraint_checking()
        cls.db.connection.create_collation('utf8mb4_bin', lambda left, right: (left > right) - (left < right))
        with cls.db.schema_editor() as schema:
            for model in (ApiCase, ApiMockConfig, ApiCaseCallbackRun, ApiMockRequestLog):
                schema.create_model(model)
        cls.db.disable_constraint_checking()
        cls.settings = override_settings(DATABASE_ROUTERS=[CallbackTestRouter()])
        cls.settings.enable()

    @classmethod
    def tearDownClass(cls):
        cls.settings.disable()
        cls.db.close()
        del connections['callback_test']
        connections.databases.pop('callback_test', None)
        super().tearDownClass()

    def setUp(self):
        real_atomic = transaction.atomic
        patches = [patch('src.apps.auto_api.services.callbacks.callback.acquire_mysql_lock', return_value=True),
                   patch('src.apps.auto_api.services.callbacks.callback.release_mysql_lock'),
                   patch('src.apps.auto_api.selectors.callback.ApiCallbackSelector.require_access'),
                   patch('src.apps.auto_api.services.callbacks.callback.transaction.atomic',
                         side_effect=lambda *args, **kwargs: real_atomic(
                             using='callback_test', savepoint=kwargs.get('savepoint', True))),
                   patch('src.apps.system.services.configuration.system_config.SystemConfigService.get_ranged_int',
                         side_effect=lambda key: {'MOCK_CALLBACK_ENABLED': 1, 'MOCK_CALLBACK_MAX_ACTIVE': 100,
                            'MOCK_CALLBACK_PRODUCT_MAX_ACTIVE': 50, 'MOCK_CALLBACK_EVIDENCE_KB': 256,
                            'MOCK_CALLBACK_EVIDENCE_DAYS': 7,
                            'MOCK_REQUEST_MAX_KB': 1024, 'MOCK_RESPONSE_MAX_KB': 1024}.get(key, 32)),
                   patch('src.apps.user.selectors.querysets.UserQuerySelector.user')]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        # 不触碰配置数据库或用户数据；只清空本测试独占的内存连接。
        with self.db.cursor() as cursor:
            for model in (ApiMockRequestLog, ApiCaseCallbackRun, ApiMockConfig, ApiCase):
                cursor.execute(f'DELETE FROM {self.db.ops.quote_name(model._meta.db_table)}')
        self.case = ApiCase.objects.create(id=1, project_product_id=1, module_id=1, case_people_id=1,
                                          name='callback-test', callback_checks=[callback_rule()])
        self.mock = ApiMockConfig.objects.create(id=1, project_product_id=1, name='callback-test',
            mock_key='callback', method=1, path='/', record_call_log=False,
            config={'methods': [], 'assertions': [], 'rules': [],
                    'default_response': {'status_code': 200, 'body_type': 'json', 'body': '{}'}})
        self.payload = {'id': 1, 'mock_key': 'callback', 'method': 1, 'path': '/', 'enabled': True,
                        'record_call_log': False, 'config': self.mock.config}

    def register(self, event='event-1'):
        return ApiCallbackService.register(case=self.case, step=SimpleNamespace(id=1), test_env=1,
            execution_key=event, test_data=SimpleNamespace(get_cache=lambda _: event))

    def deliver(self, event='event-1', *, pretty=False):
        body = json.dumps({'header': {'event_id': event}}, separators=None if pretty else (',', ':'))
        request = RequestFactory().post('/api/mock/callback/', data=body, content_type='application/json')
        return MockRuntimeService.execute(self.payload, request, '/')

    def test_early_callback_closes_run_even_with_regular_logging_off(self):
        ids = self.register()
        result = self.deliver()
        run = ApiCaseCallbackRun.objects.get(pk=ids[0])
        self.assertEqual(result.status_code, 200)
        self.assertEqual(run.status, CallbackRunStatus.PASSED)
        self.assertIsNone(run.active_key)
        self.assertEqual(run.deliveries.count(), 1)
        evidence = run.deliveries.get()
        self.assertTrue(evidence.callback_evidence['evidence_complete'])
        self.assertTrue(evidence.assertion_passed)

    def register_general(self, event='general-1'):
        self.case.callback_checks[0]['checks'] = [{'key': 'general', 'type': 'field',
            'source': 'envelope_json', 'field': '$.header.event_id',
            'assertions': [general_assertion('${{expected}}')]}]
        data = ObtainTestData()
        data.set_cache('callback_run_id', event)
        data.set_cache('expected', event)
        return ApiCallbackService.register(case=self.case, step=SimpleNamespace(id=1), test_env=1,
            execution_key=event, test_data=data)[0]

    def test_general_context_is_isolated_and_removed_when_finished(self):
        first = self.register_general('first-event')
        second = self.register_general('second-event')
        self.assertIn('_assertion_context', ApiCaseCallbackRun.objects.get(pk=first).mock_snapshot)
        self.deliver('second-event')
        self.deliver('first-event')
        for pk in (first, second):
            run = ApiCaseCallbackRun.objects.get(pk=pk)
            self.assertEqual(run.status, CallbackRunStatus.PASSED)
            self.assertNotIn('_assertion_context', run.mock_snapshot)
            self.assertTrue(run.deliveries.get().assertion_results[0]['assertions'])

    def test_general_method_validation_happens_before_registering(self):
        self.case.callback_checks[0]['checks'] = [{'key': 'invalid', 'type': 'field',
            'source': 'envelope_json', 'field': '$.header.event_id',
            'assertions': [general_assertion('expected', method='not_an_assertion')]}]
        with self.assertRaises(AutoApiError):
            ApiCallbackService.validate_config(self.case.callback_checks, 1)
        self.assertFalse(ApiCaseCallbackRun.objects.exists())

    def test_general_context_is_removed_on_cancel_and_timeout(self):
        pk = self.register_general()
        ApiCallbackService.cancel([pk])
        self.assertNotIn('_assertion_context', ApiCaseCallbackRun.objects.get(pk=pk).mock_snapshot)
        pk = self.register_general('expired')
        ApiCaseCallbackRun.objects.filter(pk=pk).update(deadline=timezone.now() - timedelta(seconds=1))
        ApiCallbackService.expire_waiting()
        self.assertNotIn('_assertion_context', ApiCaseCallbackRun.objects.get(pk=pk).mock_snapshot)

    def test_unreadable_general_context_returns_infrastructure_failure(self):
        pk = self.register_general()
        run = ApiCaseCallbackRun.objects.get(pk=pk)
        run.mock_snapshot['_assertion_context'] = 'invalid'
        run.save(update_fields=['mock_snapshot'])
        with self.assertRaises(MockRuntimeLookupError) as error:
            self.deliver('general-1')
        self.assertEqual(error.exception.status_code, 503)
        self.assertEqual(run.deliveries.count(), 0)

    def test_failure_does_not_change_observation_response(self):
        ids = self.register()
        result = self.deliver(pretty=True)
        run = ApiCaseCallbackRun.objects.get(pk=ids[0])
        self.assertEqual(result.status_code, 200)
        self.assertEqual(run.status, CallbackRunStatus.FAILED)
        self.assertFalse(result.assertion_passed)

    def test_strict_mode_uses_explicit_failure_response(self):
        self.case.callback_checks[0].update(response_mode='strict', failure_status=422)
        ids = self.register()
        result = self.deliver(pretty=True)
        self.assertEqual(result.status_code, 422)
        self.assertEqual(ApiCaseCallbackRun.objects.get(pk=ids[0]).deliveries.get().response_status, 422)

    def test_30_interleaved_runs_do_not_consume_each_others_requests(self):
        ids = [self.register(f'event-{index}')[0] for index in range(30)]
        for index in reversed(range(30)):
            self.deliver(f'event-{index}')
        for index, run_id in enumerate(ids):
            run = ApiCaseCallbackRun.objects.get(pk=run_id)
            self.assertEqual(run.status, CallbackRunStatus.PASSED)
            self.assertEqual(run.deliveries.get().callback_evidence['event_id'], f'event-{index}')

    def test_ambiguous_registration_is_rejected(self):
        self.register()
        with self.assertRaises(AutoApiError):
            self.register()

    def test_completed_correlation_cannot_be_reused_for_stale_callback(self):
        self.register()
        self.deliver()
        with self.assertRaises(AutoApiError):
            self.register()

    def test_duplicate_delivery_limit_is_observed(self):
        self.case.callback_checks[0].update(observation_seconds=5, max_deliveries=1)
        ids = self.register()
        self.deliver()
        self.deliver()
        self.assertEqual(ApiCaseCallbackRun.objects.get(pk=ids[0]).status, CallbackRunStatus.FAILED)

    def test_exact_event_count_does_not_pass_early(self):
        self.case.callback_checks[0].update(observation_seconds=5, events={'mode': 'exact', 'count': 1})
        ids = self.register()
        self.deliver()
        run = ApiCaseCallbackRun.objects.get(pk=ids[0])
        self.assertEqual(run.status, CallbackRunStatus.WAITING)

    def test_evidence_size_limit_never_passes_on_truncated_content(self):
        ids = self.register()
        body = json.dumps({'header': {'event_id': 'event-1'}, 'text': 'x' * (257 * 1024)}, separators=(',', ':'))
        request = RequestFactory().post('/api/mock/callback/', data=body, content_type='application/json')
        MockRuntimeService.execute(self.payload, request, '/')
        run = ApiCaseCallbackRun.objects.get(pk=ids[0])
        self.assertEqual(run.status, CallbackRunStatus.FAILED)
        delivery = run.deliveries.get()
        self.assertFalse(delivery.callback_evidence['evidence_complete'])
        self.assertEqual(delivery.callback_evidence['raw_body_base64'], '')
        self.assertEqual(delivery.callback_evidence['body_length'], len(body.encode()))

    def test_different_correlation_fields_cannot_overlap_active_runs(self):
        self.register()
        self.case.callback_checks[0]['correlation']['source'] = 'header'
        self.case.callback_checks[0]['correlation']['field'] = 'X-Event'
        with self.assertRaises(AutoApiError):
            self.register('event-2')

    def test_failed_evidence_commit_marks_run_failed_when_storage_recovers(self):
        from django.db import OperationalError
        ids = self.register()
        with patch.object(ApiMockRequestLog.objects, 'create', side_effect=OperationalError('unavailable')):
            with self.assertRaises(MockRuntimeLookupError):
                self.deliver()
        self.assertEqual(ApiCaseCallbackRun.objects.get(pk=ids[0]).status, CallbackRunStatus.FAILED)

    def test_timeouts_release_active_slot(self):
        ids = self.register()
        run = ApiCaseCallbackRun.objects.get(pk=ids[0])
        run.deadline = timezone.now() - timedelta(seconds=1)
        ApiCallbackService.advance(run)
        self.assertEqual(run.status, CallbackRunStatus.TIMEOUT)
        self.assertIsNone(run.active_key)

    def test_retries_count_as_one_event_and_two_deliveries(self):
        self.case.callback_checks[0]['observation_seconds'] = 5
        ids = self.register()
        self.deliver()
        self.deliver()
        run = ApiCaseCallbackRun.objects.get(pk=ids[0])
        self.assertEqual(run.deliveries.count(), 2)
        self.assertEqual(len({item.callback_evidence['event_id'] for item in run.deliveries.all()}), 1)
        self.assertEqual(run.status, CallbackRunStatus.WAITING)
        run.observation_deadline = timezone.now() - timedelta(seconds=1)
        ApiCallbackService.advance(run)
        self.assertEqual(run.status, CallbackRunStatus.PASSED)

    def test_cancellation_and_late_callback_do_not_change_result(self):
        ids = self.register()
        ApiCallbackService.cancel(ids)
        self.deliver()
        run = ApiCaseCallbackRun.objects.get(pk=ids[0])
        self.assertEqual(run.status, CallbackRunStatus.CANCELLED)
        self.assertEqual(run.deliveries.count(), 0)

    def test_database_failure_returns_503_not_fake_success(self):
        from django.db import OperationalError
        self.register()
        with patch.object(ApiMockRequestLog.objects, 'create', side_effect=OperationalError('unavailable')):
            with self.assertRaises(MockRuntimeLookupError) as error:
                self.deliver()
        self.assertEqual(error.exception.status_code, 503)

    def test_config_change_fails_closed(self):
        self.register()
        self.mock.path = '/changed'
        self.mock.save(update_fields=['path'])
        with self.assertRaises(MockRuntimeLookupError) as error:
            self.deliver()
        self.assertEqual(error.exception.status_code, 503)

    def test_retry_minimum_count_and_interval_are_enforced(self):
        self.case.callback_checks[0].update(observation_seconds=5, min_deliveries=2,
                                           min_retry_interval_ms=10000)
        ids = self.register()
        self.deliver()
        self.assertEqual(ApiCaseCallbackRun.objects.get(pk=ids[0]).status, CallbackRunStatus.WAITING)
        self.deliver()
        self.assertEqual(ApiCaseCallbackRun.objects.get(pk=ids[0]).status, CallbackRunStatus.FAILED)

    def test_retention_clears_payload_but_keeps_result_and_dedup(self):
        ids = self.register()
        self.deliver()
        run = ApiCaseCallbackRun.objects.get(pk=ids[0])
        before = ApiCallbackService.summary(run)
        ApiCaseCallbackRun.objects.filter(pk=ids[0]).update(finished_at=timezone.now() - timedelta(days=8))
        ApiCallbackService.cleanup_evidence(timezone.now() - timedelta(days=30), 100)
        delivery = ApiMockRequestLog.objects.get(callback_run_id=ids[0])
        self.assertTrue(delivery.callback_evidence['evidence_expired'])
        self.assertEqual(delivery.callback_evidence['raw_body_base64'], '')
        self.assertTrue(delivery.assertion_passed)
        self.assertEqual(ApiCallbackService.summary(run), before)
        with self.assertRaises(AutoApiError):
            self.register()

    def test_download_returns_exact_bytes_and_requires_export(self):
        from src.apps.auto_api.selectors.callback import ApiCallbackSelector
        ids = self.register()
        self.deliver()
        delivery = ApiMockRequestLog.objects.get(callback_run_id=ids[0])
        with patch('src.apps.auto_api.selectors.callback.PermissionMenuService.permission_keys_for_user',
                   return_value={'api.case:read', 'api.mock:read'}):
            with self.assertRaises(AutoApiError):
                ApiCallbackSelector.download(user=SimpleNamespace(id=1), case_id=1,
                                             run_id=ids[0], delivery_id=delivery.id)
        with patch('src.apps.auto_api.selectors.callback.PermissionMenuService.permission_keys_for_user',
                   return_value={'api.mock:read'}), patch(
                    'src.apps.auto_api.selectors.callback.ProjectProductScopeService.has_project_product',
                    return_value=True):
            raw = ApiCallbackSelector.download(user=SimpleNamespace(id=1), case_id=1,
                                               run_id=ids[0], delivery_id=delivery.id)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), delivery.callback_evidence['body_sha256'])

    def test_encrypted_callback_signature_and_original_plaintext_are_preserved(self):
        from src.apps.auto_api.tests.test_mock_runtime import MockRuntimeServiceTests
        self.mock.config['request_decryption'] = {'type': 'lark_event', 'encrypt_key': 'synthetic-key',
                                                  'verification_token': ''}
        self.mock.save(update_fields=['config'])
        self.case.callback_checks[0]['correlation']['source'] = 'business_json'
        self.case.callback_checks[0]['checks'].append({'key': 'sign', 'type': 'lark_signature', 'source': 'raw_body'})
        ids = self.register()
        envelope = {'encrypt': MockRuntimeServiceTests.encrypt_lark_event(
            {'header': {'event_id': 'event-1'}, 'text': '合成数据'}, 'synthetic-key',
        )}
        raw = json.dumps(envelope, separators=(',', ':')).encode()
        signature = hashlib.sha256(b'123noncesynthetic-key' + raw).hexdigest()
        request = RequestFactory().post('/api/mock/callback/', data=raw, content_type='application/json',
            HTTP_X_LARK_REQUEST_TIMESTAMP='123', HTTP_X_LARK_REQUEST_NONCE='nonce', HTTP_X_LARK_SIGNATURE=signature)
        MockRuntimeService.execute(self.payload, request, '/')
        run = ApiCaseCallbackRun.objects.get(pk=ids[0])
        self.assertEqual(run.status, CallbackRunStatus.PASSED)
        delivery = run.deliveries.get()
        self.assertIn(': ', delivery.callback_evidence['business_body'])
        self.assertEqual(delivery.callback_evidence['body_sha256'], hashlib.sha256(raw).hexdigest())

    def test_response_records_duration_without_duplicate_async_log(self):
        ids = self.register()
        result = self.deliver()
        request = RequestFactory().post('/api/mock/callback/', data='{}', content_type='application/json')
        with patch.object(MockRuntimeService, 'submit_log') as submit:
            MockRuntimeService.record_response(self.payload, request, result, 2005)
        submit.assert_not_called()
        record = ApiMockRequestLog.objects.get(callback_run_id=ids[0])
        self.assertEqual(result.callback_log_id, record.id)
        self.assertEqual(record.duration_ms, 2005)
        self.assertEqual(ApiMockRequestLog.objects.count(), 1)

    def test_summary_archives_full_assertions_through_existing_result_storage(self):
        from django.core.files.storage import InMemoryStorage
        from src.apps.test_center.services.results.execution_result import ExecutionResultService
        ids = self.register()
        self.deliver(pretty=True)
        from src.apps.auto_api.schemas.execution import ApiAssertionResult
        run = ApiCaseCallbackRun.objects.get(pk=ids[0])
        step = SimpleNamespace(ass=[ApiAssertionResult(method='普通响应断言')])
        summary = ApiCallbackService.attach_results(step, [run])[0]
        ApiCallbackService.attach_results(step, [run])
        self.assertEqual(len(step.ass), 3)
        storage = InMemoryStorage()
        with patch('src.apps.test_center.services.results.execution_result.default_storage', storage):
            key, _ = ExecutionResultService.save_result_file(
                {'callback_results': [summary], 'steps': [{'ass': [item.model_dump(mode='json') for item in step.ass]}]},
                target_type='api_case', target_id=1,
            )
        with storage.open(key, 'rb') as stream:
            archive = json.loads(stream.read())
        result = archive['callback_results'][0]
        assertion = ApiAssertionResult.model_validate(archive['steps'][0]['ass'][2])
        self.assertEqual(assertion.callback.check_key, 'compact')
        self.assertFalse(assertion.callback.passed)
        self.assertEqual(assertion.status, 0)
        self.assertEqual(result['trigger_step_key'], 'step-1')
        self.assertEqual(assertion.callback.check_type, 'json_compact')
        self.assertNotIn('check_definitions', result)
        self.assertNotIn('checks', result['delivery_results'][0])
        self.assertTrue(result['delivery_results'][0]['received_at'].endswith('+00:00'))
        self.assertNotIn('raw_body_base64', json.dumps(result))
        self.assertNotIn('request_headers', json.dumps(result))

    def test_callback_evidence_not_exposed_by_regular_mock_log_serializer(self):
        from src.apps.auto_api.api.serializers.api_mock import ApiMockRequestLogSerializer
        ids = self.register()
        self.deliver()
        record = ApiMockRequestLog.objects.get(callback_run_id=ids[0])
        serialized = ApiMockRequestLogSerializer(record).data
        self.assertNotIn('callback_evidence', serialized)
        self.assertNotIn('callback_run', serialized)
        self.assertIn('assertion_results', serialized)

    def test_timeout_and_cancellation_are_archived_without_deliveries(self):
        ids = self.register()
        run = ApiCaseCallbackRun.objects.get(pk=ids[0])
        for status in (CallbackRunStatus.TIMEOUT, CallbackRunStatus.CANCELLED):
            run.status = status
            run.error_message = '等待超时或触发中止'
            summary, assertions = ApiCallbackService.archive(run)
            self.assertEqual(summary['delivery_results'], [])
            self.assertEqual(len(assertions), 1)
            self.assertEqual(assertions[0].status, 0)
            self.assertEqual(assertions[0].callback.run_status, status)
            self.assertEqual(assertions[0].ass_msg, run.error_message)

    def test_diagnostic_failure_keeps_observed_result_without_failing_assertion(self):
        ids = self.register()
        self.deliver()
        run = ApiCaseCallbackRun.objects.get(pk=ids[0])
        delivery = run.deliveries.get()
        delivery.assertion_results = [{'key': 'compact', 'passed': False,
                                      'diagnostic': True, 'message': '仅诊断'}]
        delivery.save(update_fields=['assertion_results'])
        _, assertions = ApiCallbackService.archive(run)
        self.assertEqual(assertions[1].status, 1)
        self.assertFalse(assertions[1].callback.passed)
        self.assertTrue(assertions[1].callback.diagnostic)
        self.assertIsNone(assertions[1].actual)
        self.assertIsNone(assertions[1].expect)

    def test_manual_and_scheduled_cleanup_preserve_callback_judgement_records(self):
        from src.apps.auto_api.services.mock.mock_log_cleanup import MockRequestLogCleanupService
        ids = self.register()
        self.deliver()
        run = ApiCaseCallbackRun.objects.get(pk=ids[0])
        ordinary = ApiMockRequestLog.objects.create(mock_config=self.mock, method=1, request_path='/')
        with patch('src.apps.auto_api.services.mock.mock_log_cleanup.cache'):
            self.assertEqual(MockRequestLogCleanupService.clear_config_logs(self.mock.id), 1)
            self.assertEqual(run.deliveries.count(), 1)
            self.assertFalse(ApiMockRequestLog.objects.filter(pk=ordinary.pk).exists())
            ApiMockRequestLog.objects.create(mock_config=self.mock, method=1, request_path='/')
            self.assertEqual(MockRequestLogCleanupService.clear_all_logs(), 1)
        with patch.object(ApiCallbackService, 'enabled', return_value=False):
            with patch('src.apps.auto_api.services.mock.mock_log_cleanup.cache'):
                self.assertEqual(MockRequestLogCleanupService.clear_all_logs(), 0)
        self.assertEqual(run.deliveries.count(), 1)
        ApiCaseCallbackRun.objects.filter(pk=run.id).update(finished_at=timezone.now() - timedelta(days=8))
        MockRequestLogCleanupService.cleanup_before(timezone.now() + timedelta(seconds=1))
        record = run.deliveries.get()
        self.assertTrue(record.callback_evidence['evidence_expired'])
        self.assertEqual(record.callback_evidence['raw_body_base64'], '')
        self.assertTrue(record.assertion_passed)
        self.assertEqual(ApiCallbackService.summary(run)['deliveries'], 1)

    def test_paged_queries_still_return_evidence_with_scoped_access(self):
        from src.apps.auto_api.selectors.callback import ApiCallbackSelector
        ids = self.register()
        self.deliver()
        user = SimpleNamespace(id=1)
        with patch('src.apps.auto_api.selectors.callback.ProjectProductScopeService.has_project_product',
                   return_value=True), patch(
                   'src.apps.auto_api.selectors.callback.PermissionMenuService.is_effective_super_admin',
                   return_value=True):
            results = ApiCallbackSelector.results(user=user, case_id=1)
            page = ApiCallbackSelector.deliveries(user=user, case_id=1, run_id=ids[0])
            detail = ApiCallbackSelector.deliveries(user=user, case_id=1, run_id=ids[0],
                                                   delivery_id=page['items'][0]['id'])
        self.assertEqual(results['items'][0]['events'], 1)
        definition = results['items'][0]['check_definitions'][0]
        self.assertEqual(definition['type'], 'json_compact')
        self.assertEqual(set(definition), {'key', 'type', 'source', 'field'})
        self.assertNotIn('expected', definition)
        self.assertEqual(page['items'][0]['event_id'], 'event-1')
        self.assertTrue(page['items'][0]['evidence_complete'])
        self.assertNotIn('raw_body', page['items'][0])
        self.assertIn('event-1', detail['items'][0]['raw_body'])

    def test_event_ids_are_case_sensitive_after_reusing_mock_logs(self):
        self.case.callback_checks[0].update(observation_seconds=5, events={'mode': 'exact', 'count': 2})
        self.case.callback_checks[0]['correlation'].update(source='header', field='X-Run')
        ids = self.register('run-1')
        for event_id in ('Event-1', 'event-1'):
            request = RequestFactory().post('/api/mock/callback/',
                data=json.dumps({'header': {'event_id': event_id}}, separators=(',', ':')),
                content_type='application/json', HTTP_X_RUN='run-1')
            MockRuntimeService.execute(self.payload, request, '/')
        run = ApiCaseCallbackRun.objects.get(pk=ids[0])
        run.observation_deadline = timezone.now() - timedelta(seconds=1)
        ApiCallbackService.advance(run)
        self.assertEqual(run.status, CallbackRunStatus.PASSED)
        self.assertEqual(ApiCallbackService.summary(run)['events'], 2)

    def test_only_run_model_is_new_and_deletion_cascades_to_callback_logs(self):
        from django.apps import apps
        with self.assertRaises(LookupError):
            apps.get_model('auto_api', 'ApiCaseCallbackDelivery')
        ids = self.register()
        self.deliver()
        self.assertEqual(ApiMockRequestLog.objects.count(), 1)
        ApiCaseCallbackRun.objects.filter(pk__in=ids).delete()
        self.assertEqual(ApiMockRequestLog.objects.count(), 0)

    def test_result_step_filter_applies_before_pagination(self):
        from src.apps.auto_api.selectors.callback import ApiCallbackSelector
        first = self.register()[0]
        self.deliver()
        self.case.callback_checks[0]['trigger_step_key'] = 'step-2'
        second = ApiCallbackService.register(
            case=self.case, step=SimpleNamespace(id=2), test_env=1, execution_key='second-execution',
            test_data=SimpleNamespace(get_cache=lambda _: 'event-2'),
        )[0]
        with patch('src.apps.auto_api.selectors.callback.PermissionMenuService.is_effective_super_admin',
                   return_value=True):
            for step, expected in [('step-1', first), ('step-2', second)]:
                result = ApiCallbackSelector.results(user=SimpleNamespace(id=1), case_id=1,
                    trigger_step_key=step, page=1, page_size=1)
                self.assertEqual(result['count'], 1)
                self.assertEqual(result['items'][0]['id'], expected)
            empty = ApiCallbackSelector.results(user=SimpleNamespace(id=1), case_id=1,
                                               trigger_step_key='step-3')
            self.assertEqual(empty['count'], 0)


class CallbackPermissionTests(SimpleTestCase):
    def test_guest_cannot_read_raw_evidence_even_with_page_detail_keys(self):
        from src.apps.auto_api.selectors.callback import ApiCallbackSelector
        user = SimpleNamespace(id=1, role_id=2, is_super_admin=False, role=SimpleNamespace(name='游客'))
        with patch('src.apps.auto_api.selectors.callback.PermissionMenuService.permission_keys_for_user',
                   return_value={'api.case:read', 'api.mock:read'}):
            with self.assertRaises(AutoApiError):
                ApiCallbackSelector.require_access(user, 1)
    def test_anonymous_and_missing_mock_permission_are_denied(self):
        from src.apps.auto_api.selectors.callback import ApiCallbackSelector
        with self.assertRaises(AutoApiError):
            ApiCallbackSelector.require_access(None, 1)
        with patch('src.apps.auto_api.selectors.callback.PermissionMenuService.permission_keys_for_user',
                   return_value={'api.case:read'}):
            with self.assertRaises(AutoApiError):
                ApiCallbackSelector.require_access(SimpleNamespace(id=1), 1)

    def test_case_scope_is_required_even_with_both_detail_permissions(self):
        from src.apps.auto_api.selectors.callback import ApiCallbackSelector
        with patch('src.apps.auto_api.selectors.callback.PermissionMenuService.permission_keys_for_user',
                   return_value={'api.case:read', 'api.mock:read'}), patch(
                    'src.apps.auto_api.selectors.callback.ApiCaseConfigurationSelector.scoped_cases') as scoped:
            scoped.return_value.exists.return_value = False
            with self.assertRaises(AutoApiError):
                ApiCallbackSelector.require_access(SimpleNamespace(id=1), 1)

    def test_http_routes_have_explicit_permissions_and_bounded_queries(self):
        from django.urls import resolve
        from src.apps.auto_api.api.serializers.api_callback import CallbackQuerySerializer
        match = resolve('/api/api/case/callback/results')
        self.assertEqual(permission_for_view(match.func.cls, 'results'), 'api.case:read')
        query = CallbackQuerySerializer(data={'case_id': 1, 'page_size': 101})
        self.assertFalse(query.is_valid())
        query = CallbackQuerySerializer(data={'case_id': 1, 'trigger_step_key': 'step-2'})
        self.assertTrue(query.is_valid())
        query = CallbackQuerySerializer(data={'case_id': 1, 'trigger_step_key': 'not-a-step'})
        self.assertFalse(query.is_valid())

    def test_mcp_result_tools_are_registered_and_read_only(self):
        import inspect
        from src.interfaces.mcp.tools.api.case_tools.execution import register_case_execution_tools
        from src.interfaces.mcp.tests.test_api_case_errors import ToolRegistry
        registry = ToolRegistry()
        register_case_execution_tools(registry)
        for name in ('get_api_case_callback_results', 'get_api_case_callback_deliveries'):
            self.assertIn(name, registry.tools)
            self.assertIn('page_size', inspect.signature(registry.tools[name]).parameters)
            from src.interfaces.mcp.authentication import component_policy
            policy = component_policy(name)
            self.assertEqual(policy.permission_key, 'api.case:read')
            self.assertEqual(policy.additional_permission_keys, ('api.mock:read',))
