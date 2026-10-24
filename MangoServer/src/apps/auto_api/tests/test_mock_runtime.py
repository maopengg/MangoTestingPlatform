import base64
import hashlib
import json
import uuid
from contextlib import nullcontext
from datetime import timedelta
from queue import Full
from threading import Event
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase
from django.urls import resolve
from django.utils import timezone

from src.apps.auto_api.api.serializers.api_mock import ApiMockConfigListSerializer
from src.apps.auto_api.api.views.api_mock import ApiMockConfigViews, ApiMockRuntimeView
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.exceptions import MockRuntimeLookupError
from src.apps.auto_api.models import ApiMockRequestLog
from src.apps.auto_api.services.mock_log_cleanup import MockRequestLogCleanupService
from src.apps.auto_api.services.mock_request_decryption import MockRequestDecryptionService
from src.apps.auto_api.services.mock_runtime import (
    MOCK_LOG_GLOBAL_CLEAR_MARKER_KEY,
    MOCK_LOG_GLOBAL_CLEAR_TIMEOUT_SECONDS,
    MOCK_LOG_GLOBAL_WRITE_PAUSE_KEY,
    MockAssertionCatalog, MockConfigValidator, MockLogBatchWriter,
    MockRuntimeCache, MockRuntimeService,
)


class MockRuntimeServiceTests(SimpleTestCase):
    @staticmethod
    def encrypt_lark_event(payload: dict, encrypt_key: str) -> str:
        iv = b"0123456789abcdef"
        plaintext = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded = padder.update(plaintext) + padder.finalize()
        key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
        encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
        ciphertext = encryptor.update(padded) + encryptor.finalize()
        return base64.b64encode(iv + ciphertext).decode("ascii")

    def test_runtime_local_cache_avoids_repeated_shared_cache_reads(self):
        payload = {"id": 1, "enabled": True}
        MockRuntimeCache._local_entries.clear()
        with patch("src.apps.auto_api.services.mock_runtime.cache.get", return_value=payload) as get:
            with patch("src.apps.auto_api.services.mock_runtime.time.monotonic", side_effect=[10, 10, 10.2]):
                self.assertIs(MockRuntimeCache.load("items"), payload)
                self.assertIs(MockRuntimeCache.load("items"), payload)
        get.assert_called_once()
        MockRuntimeCache._local_entries.clear()

    def test_runtime_local_cache_expires_and_invalidates(self):
        first = {"id": 1}
        second = {"id": 2}
        MockRuntimeCache._local_entries.clear()
        with patch("src.apps.auto_api.services.mock_runtime.cache.get", side_effect=[first, second, second]) as get:
            with patch("src.apps.auto_api.services.mock_runtime.cache.delete") as delete:
                with patch("src.apps.auto_api.services.mock_runtime.time.monotonic",
                           side_effect=[10, 10, 11.1, 11.1, 11.2, 11.2]):
                    self.assertIs(MockRuntimeCache.load("items"), first)
                    self.assertIs(MockRuntimeCache.load("items"), second)
                    MockRuntimeCache.invalidate("items")
                    self.assertIs(MockRuntimeCache.load("items"), second)
        self.assertEqual(get.call_count, 3)
        delete.assert_called_once_with(MockRuntimeCache.key("items"))
        MockRuntimeCache._local_entries.clear()

    def test_runtime_cache_only_reveals_decryption_secret_in_local_payload(self):
        stored = MockRequestDecryptionService.normalize_for_storage({
            "type": "lark_event",
            "encrypt_key": "encrypt-key",
            "verification_token": "verification-token",
        })
        payload = {"id": 1, "config": {"request_decryption": stored}}
        MockRuntimeCache._local_entries.clear()
        with patch("src.apps.auto_api.services.mock_runtime.cache.get", return_value=payload):
            runtime = MockRuntimeCache.load("lark-event")

        self.assertNotIn("encrypt_key", payload["config"]["request_decryption"])
        self.assertEqual(runtime["config"]["request_decryption"]["encrypt_key"], "encrypt-key")
        self.assertEqual(runtime["config"]["request_decryption"]["verification_token"], "verification-token")
        MockRuntimeCache._local_entries.clear()

    def test_log_queue_full_writes_in_request_without_dropping(self):
        payload = {"trace_id": "mock-test"}
        writer = MockLogBatchWriter()
        with patch.object(writer, "_ensure_started"):
            with patch.object(writer._queue, "put_nowait", side_effect=Full):
                with patch.object(writer, "_write_batch") as write_batch:
                    writer.submit(payload)
        write_batch.assert_called_once_with([payload])

    def test_log_batch_flushes_at_count_threshold(self):
        writer = MockLogBatchWriter(batch_size=3, flush_seconds=10)
        flushed = Event()
        batches = []

        def record_batch(payloads):
            batches.append(payloads)
            flushed.set()

        with patch.object(writer, "_write_batch", side_effect=record_batch):
            try:
                for index in range(3):
                    writer.submit({"trace_id": f"mock-{index}"})
                self.assertTrue(flushed.wait(1))
            finally:
                writer.close()
        self.assertEqual(len(batches[0]), 3)

    def test_log_batch_flushes_after_interval_and_on_close(self):
        writer = MockLogBatchWriter(flush_seconds=0.05)
        flushed = Event()
        batches = []

        def record_batch(payloads):
            batches.append(payloads)
            flushed.set()

        with patch.object(writer, "_write_batch", side_effect=record_batch):
            try:
                writer.submit({"trace_id": "mock-timed"})
                self.assertTrue(flushed.wait(1))
                writer.submit({"trace_id": "mock-close"})
            finally:
                writer.close()
        self.assertEqual([item["trace_id"] for batch in batches for item in batch], ["mock-timed", "mock-close"])

    def test_log_batch_caps_payload_bytes(self):
        writer = MockLogBatchWriter(flush_seconds=10, max_batch_bytes=40)
        flushed = Event()
        batches = []

        def record_batch(payloads):
            batches.append(payloads)
            flushed.set()

        with patch.object(writer, "_write_batch", side_effect=record_batch):
            try:
                writer.submit({"trace_id": "mock-payload-larger-than-limit"})
                self.assertTrue(flushed.wait(1))
            finally:
                writer.close()
        self.assertEqual(len(batches[0]), 1)

    def test_log_batch_uses_bulk_create(self):
        writer = MockLogBatchWriter()
        called_at = timezone.now()
        payloads = [
            {"trace_id": "mock-1", "create_time": called_at, "mock_config_id": 1},
            {"trace_id": "mock-2", "create_time": called_at, "mock_config_id": 1},
        ]
        with patch("src.apps.auto_api.services.mock_runtime.close_old_connections"):
            with patch("src.apps.auto_api.services.mock_runtime.transaction.atomic", return_value=nullcontext()):
                with patch("src.apps.auto_api.services.mock_runtime.ApiMockConfig.objects.select_for_update"):
                    with patch("src.apps.auto_api.services.mock_runtime.cache.get_many", return_value={}):
                        with patch(
                                "src.apps.auto_api.services.mock_runtime.ApiMockRequestLog.objects.bulk_create") as bulk_create:
                            writer._write_batch(payloads)
        self.assertEqual([item.trace_id for item in bulk_create.call_args.args[0]], ["mock-1", "mock-2"])
        self.assertTrue(all(item.create_time == called_at for item in bulk_create.call_args.args[0]))
        self.assertEqual(bulk_create.call_args.kwargs["batch_size"], 1500)

    def test_log_batch_ignores_entries_from_before_clear(self):
        writer = MockLogBatchWriter()
        cleared_at = timezone.now()
        payloads = [
            {"trace_id": "mock-old", "create_time": cleared_at - timedelta(seconds=1), "mock_config_id": 1},
            {"trace_id": "mock-new", "create_time": cleared_at + timedelta(seconds=1), "mock_config_id": 1},
        ]
        with patch("src.apps.auto_api.services.mock_runtime.close_old_connections"):
            with patch("src.apps.auto_api.services.mock_runtime.transaction.atomic", return_value=nullcontext()):
                with patch("src.apps.auto_api.services.mock_runtime.ApiMockConfig.objects.select_for_update"):
                    with patch("src.apps.auto_api.services.mock_runtime.cache.get_many",
                               return_value={"mock:log:cleared:1": cleared_at}):
                        with patch(
                                "src.apps.auto_api.services.mock_runtime.ApiMockRequestLog.objects.bulk_create") as bulk_create:
                            writer._write_batch(payloads)
        self.assertEqual([item.trace_id for item in bulk_create.call_args.args[0]], ["mock-new"])

    def test_log_batch_ignores_entries_from_before_global_clear(self):
        writer = MockLogBatchWriter()
        cleared_at = timezone.now()
        payloads = [
            {"trace_id": "mock-old", "create_time": cleared_at - timedelta(seconds=1), "mock_config_id": 1},
            {"trace_id": "mock-new", "create_time": cleared_at + timedelta(seconds=1), "mock_config_id": 1},
        ]
        with patch("src.apps.auto_api.services.mock_runtime.close_old_connections"):
            with patch("src.apps.auto_api.services.mock_runtime.transaction.atomic", return_value=nullcontext()):
                with patch("src.apps.auto_api.services.mock_runtime.ApiMockConfig.objects.select_for_update"):
                    with patch(
                            "src.apps.auto_api.services.mock_runtime.cache.get_many",
                            return_value={MOCK_LOG_GLOBAL_CLEAR_MARKER_KEY: cleared_at},
                    ):
                        with patch(
                                "src.apps.auto_api.services.mock_runtime.ApiMockRequestLog.objects.bulk_create"
                        ) as bulk_create:
                            writer._write_batch(payloads)
        self.assertEqual([item.trace_id for item in bulk_create.call_args.args[0]], ["mock-new"])

    def test_log_batch_does_not_write_while_global_clear_is_paused(self):
        writer = MockLogBatchWriter()
        payload = {"trace_id": "mock-paused", "create_time": timezone.now(), "mock_config_id": 1}
        with patch("src.apps.auto_api.services.mock_runtime.close_old_connections"):
            with patch("src.apps.auto_api.services.mock_runtime.transaction.atomic", return_value=nullcontext()):
                with patch("src.apps.auto_api.services.mock_runtime.ApiMockConfig.objects.select_for_update"):
                    with patch(
                            "src.apps.auto_api.services.mock_runtime.cache.get_many",
                            return_value={MOCK_LOG_GLOBAL_WRITE_PAUSE_KEY: True},
                    ):
                        with patch(
                                "src.apps.auto_api.services.mock_runtime.ApiMockRequestLog.objects.bulk_create"
                        ) as bulk_create:
                            writer._write_batch([payload])
        bulk_create.assert_not_called()

    def test_public_mock_route_is_under_api_prefix(self):
        match = resolve('/api/mock/items/contracts/123')

        self.assertEqual(match.func.view_class, ApiMockRuntimeView)
        self.assertEqual(match.kwargs, {
            'mock_key': 'items',
            'remaining_path': '/contracts/123',
        })

    def test_mock_config_detail_view_uses_callable_retrieve_action(self):
        view = ApiMockConfigViews.as_view({"get": "retrieve"})

        self.assertEqual(view.actions["get"], "retrieve")
        self.assertTrue(callable(ApiMockConfigViews.retrieve))

    def test_mock_log_view_exposes_clear_action(self):
        view = ApiMockConfigViews.as_view({"get": "logs", "delete": "clear_logs"})

        self.assertEqual(view.actions["delete"], "clear_logs")
        self.assertTrue(callable(ApiMockConfigViews.clear_logs))

    def test_mock_log_view_exposes_clear_all_action(self):
        match = resolve("/api/api/mock/config/logs/all")

        self.assertEqual(match.func.actions["delete"], "clear_all_logs")
        self.assertTrue(callable(ApiMockConfigViews.clear_all_logs))

    def test_clear_all_mock_logs_pauses_writes_and_truncates_mysql_table(self):
        cleared_at = timezone.now()
        cursor = MagicMock()
        mocked_connection = MagicMock()
        mocked_connection.vendor = "mysql"
        mocked_connection.ops.quote_name.return_value = "`api_mock_request_log`"
        mocked_connection.cursor.return_value.__enter__.return_value = cursor

        with patch(
                "src.apps.auto_api.services.mock_log_cleanup.timezone.now",
                return_value=cleared_at,
        ):
            with patch("src.apps.auto_api.services.mock_log_cleanup.cache.set_many") as set_many:
                with patch("src.apps.auto_api.services.mock_log_cleanup.cache.delete") as cache_delete:
                    with patch(
                            "src.apps.auto_api.services.mock_log_cleanup.ApiMockRequestLog.objects.count",
                            return_value=123,
                    ):
                        with patch(
                                "src.apps.auto_api.services.mock_log_cleanup.connection",
                                mocked_connection,
                        ):
                            deleted = MockRequestLogCleanupService.clear_all_logs()

        self.assertEqual(deleted, 123)
        set_many.assert_called_once_with(
            {
                MOCK_LOG_GLOBAL_WRITE_PAUSE_KEY: True,
                MOCK_LOG_GLOBAL_CLEAR_MARKER_KEY: cleared_at,
            },
            MOCK_LOG_GLOBAL_CLEAR_TIMEOUT_SECONDS,
        )
        cursor.execute.assert_called_once_with("TRUNCATE TABLE `api_mock_request_log`")
        cache_delete.assert_called_once_with(MOCK_LOG_GLOBAL_WRITE_PAUSE_KEY)

    def test_clear_all_mock_logs_removes_marker_when_truncate_fails(self):
        mocked_connection = MagicMock()
        mocked_connection.vendor = "mysql"
        mocked_connection.ops.quote_name.return_value = "`api_mock_request_log`"
        mocked_connection.cursor.return_value.__enter__.return_value.execute.side_effect = RuntimeError("boom")

        with patch("src.apps.auto_api.services.mock_log_cleanup.cache.set_many"):
            with patch("src.apps.auto_api.services.mock_log_cleanup.cache.delete") as cache_delete:
                with patch(
                        "src.apps.auto_api.services.mock_log_cleanup.ApiMockRequestLog.objects.count",
                        return_value=1,
                ):
                    with patch(
                            "src.apps.auto_api.services.mock_log_cleanup.connection",
                            mocked_connection,
                    ):
                        with self.assertRaisesRegex(RuntimeError, "boom"):
                            MockRequestLogCleanupService.clear_all_logs()

        self.assertEqual(
            cache_delete.call_args_list,
            [
                call(MOCK_LOG_GLOBAL_WRITE_PAUSE_KEY),
                call(MOCK_LOG_GLOBAL_CLEAR_MARKER_KEY),
            ],
        )

    def test_clear_mock_logs_creates_snapshot_before_batch_delete(self):
        locked_queryset = MagicMock()
        locked_queryset.only.return_value.get.return_value = SimpleNamespace(id=7)
        log_queryset = MagicMock()
        cleared_at = timezone.now()

        with patch(
                "src.apps.auto_api.services.mock_log_cleanup.transaction.atomic",
                return_value=nullcontext(),
        ):
            with patch(
                    "src.apps.auto_api.services.mock_log_cleanup.ApiMockConfig.objects.select_for_update",
                    return_value=locked_queryset,
            ):
                with patch(
                        "src.apps.auto_api.services.mock_log_cleanup.timezone.now",
                        return_value=cleared_at,
                ):
                    with patch("src.apps.auto_api.services.mock_log_cleanup.cache.set") as cache_set:
                        with patch(
                                "src.apps.auto_api.services.mock_log_cleanup.ApiMockRequestLog.objects.filter",
                                return_value=log_queryset,
                        ) as filter_logs:
                            with patch.object(
                                    MockRequestLogCleanupService,
                                    "_delete_in_batches",
                                    return_value=23,
                            ) as delete_in_batches:
                                deleted = MockRequestLogCleanupService.clear_config_logs(7, batch_size=100)

        self.assertEqual(deleted, 23)
        locked_queryset.only.assert_called_once_with("id")
        locked_queryset.only.return_value.get.assert_called_once_with(pk=7)
        cache_set.assert_called_once_with("mock:log:cleared:7", cleared_at, 3600)
        filter_logs.assert_called_once_with(mock_config_id=7, create_time__lte=cleared_at)
        delete_in_batches.assert_called_once_with(log_queryset, batch_size=100)

    def test_mock_log_batch_delete_uses_independent_transactions(self):
        queryset = MagicMock()
        id_values = queryset.order_by.return_value.values_list.return_value
        id_values.__getitem__.side_effect = [[1, 2], [3], []]
        first_delete = MagicMock()
        first_delete.delete.return_value = (2, {"auto_api.ApiMockRequestLog": 2})
        second_delete = MagicMock()
        second_delete.delete.return_value = (1, {"auto_api.ApiMockRequestLog": 1})

        with patch(
                "src.apps.auto_api.services.mock_log_cleanup.transaction.atomic",
                side_effect=[nullcontext(), nullcontext()],
        ) as atomic:
            with patch(
                    "src.apps.auto_api.services.mock_log_cleanup.ApiMockRequestLog.objects.filter",
                    side_effect=[first_delete, second_delete],
            ) as filter_logs:
                deleted = MockRequestLogCleanupService._delete_in_batches(queryset, batch_size=2)

        self.assertEqual(deleted, 3)
        self.assertEqual(atomic.call_count, 2)
        self.assertEqual(filter_logs.call_args_list, [call(id__in=[1, 2]), call(id__in=[3])])
        self.assertEqual(queryset.order_by.call_count, 3)

    def test_mock_log_export_route_uses_export_action(self):
        match = resolve("/api/api/mock/config/logs/export")

        self.assertEqual(match.func.actions["get"], "export_logs")
        self.assertTrue(callable(ApiMockConfigViews.export_logs))

    def test_mock_log_csv_contains_details_and_escapes_formula_cells(self):
        item = ApiMockRequestLog(
            create_time=timezone.now(),
            mock_config_id=1,
            trace_id="mock-trace",
            rule_key="matched-rule",
            method=1,
            request_path="/events",
            request_data={
                "query": {"source": "test"},
                "headers": {"content-type": "application/json"},
                "body": "=dangerous-formula",
            },
            assertion_passed=False,
            assertion_results=[{
                "name": "事件类型",
                "passed": False,
                "message": "实际值与预期值不一致",
            }],
            response_status=200,
            response_data={
                "headers": {"x-mock": "1"},
                "body": '{"ok":false}',
                "content_type": "application/json",
            },
            duration_ms=3,
            client_ip="127.0.0.1",
        )

        row = ApiMockConfigViews._log_csv_row(item)

        self.assertEqual(row[1], "警告")
        self.assertIn("事件类型（实际值与预期值不一致）", row[2])
        self.assertEqual(row[3], "POST")
        self.assertEqual(row[12], "'=dangerous-formula")
        self.assertEqual(row[15], '{"ok":false}')

    def test_mock_log_csv_file_is_complete_and_has_content_length(self):
        item = SimpleNamespace(
            create_time=timezone.now(),
            error_message="",
            assertion_passed=True,
            assertion_results=[],
            method=1,
            response_status=200,
            request_path="/events",
            trace_id="mock-trace",
            rule_key=None,
            duration_ms=3,
            client_ip="127.0.0.1",
            request_data={"query": {}, "headers": {}, "body": "{}"},
            response_data={"headers": {}, "body": '{"ok":true}', "content_type": "application/json"},
        )

        class Queryset:
            @staticmethod
            def iterator(chunk_size):
                self.assertEqual(chunk_size, 1000)
                return iter([item])

        csv_file, content_length = ApiMockConfigViews._build_log_csv_file(Queryset())
        try:
            content = csv_file.read()
        finally:
            csv_file.close()

        self.assertEqual(content_length, len(content))
        self.assertGreater(content_length, 0)
        self.assertTrue(content.startswith("\ufeff".encode("utf-8")))
        self.assertIn(b"mock-trace", content)

    def test_mock_serializer_displays_multiple_methods(self):
        self.assertEqual(
            ApiMockConfigListSerializer.get_method_name(
                SimpleNamespace(method=0, config={"methods": [0, 1]}),
            ),
            "GET / POST",
        )
        self.assertEqual(
            ApiMockConfigListSerializer.get_method_name(SimpleNamespace(method=0, config={"methods": []})),
            "全部",
        )

    def build_config(self):
        return {
            "assertions": [
                {
                    "key": "id-required",
                    "name": "ID必填",
                    "enabled": True,
                    "source": "path",
                    "field": "item_id",
                    "operator": "p_is_not_none",
                    "expected": None,
                },
                {
                    "key": "token-format",
                    "name": "Token格式",
                    "enabled": True,
                    "source": "header",
                    "field": "Authorization",
                    "operator": "p_matches_regex",
                    "expected": "^Bearer .+$",
                },
            ],
            "rules": [
                {
                    "key": "found",
                    "name": "命中",
                    "enabled": True,
                    "matchers": [
                        {
                            "key": "id-is-1",
                            "source": "path",
                            "field": "item_id",
                            "operator": "p_is_equal_to",
                            "expected": "1",
                        }
                    ],
                    "response": {
                        "status_code": 200,
                        "content_type": "application/json",
                        "headers": {},
                        "body_type": "json",
                        "body": "{\"ok\":true}",
                        "delay_ms": 0,
                    },
                }
            ],
            "default_response": {
                "status_code": 404,
                "content_type": "application/json",
                "headers": {},
                "body_type": "json",
                "body": "{\"ok\":false}",
                "delay_ms": 0,
            },
        }

    def test_validator_accepts_complete_config(self):
        result = MockConfigValidator.validate_config(self.build_config())
        self.assertEqual(len(result["assertions"]), 2)
        self.assertEqual(result["rules"][0]["key"], "found")

    def test_validator_removes_legacy_failure_message(self):
        config = self.build_config()
        config["assertions"][0]["message"] = "旧失败提示"

        result = MockConfigValidator.validate_config(config)

        self.assertNotIn("message", result["assertions"][0])

    def test_validator_rejects_removed_legacy_operator(self):
        config = self.build_config()
        config["assertions"][0]["operator"] = "exists"

        with self.assertRaises(AutoApiError):
            MockConfigValidator.validate_config(config)

    def test_debug_runs_all_assertions_and_uses_first_matching_rule(self):
        config = SimpleNamespace(method=0, path="/items/{item_id}", config=self.build_config())
        result = MockRuntimeService.debug(
            config,
            {
                "method": "GET",
                "path": "/items/1",
                "headers": {"Authorization": "invalid"},
            },
        )
        self.assertFalse(result["assertion_passed"])
        self.assertEqual(len(result["assertion_results"]), 2)
        self.assertTrue(result["assertion_results"][0]["passed"])
        self.assertFalse(result["assertion_results"][1]["passed"])
        self.assertEqual(result["matched_rule_key"], "found")
        self.assertFalse(result["used_default_response"])

    def test_debug_uses_default_response_when_rule_does_not_match(self):
        config = SimpleNamespace(method=0, path="/items/{item_id}", config=self.build_config())
        result = MockRuntimeService.debug(config, {"path": "/items/2", "headers": {}})
        self.assertTrue(result["used_default_response"])
        self.assertEqual(result["response_preview"]["status_code"], 404)

    def test_runtime_decrypts_lark_event_before_json_body_assertion(self):
        encrypt_key = "test-encrypt-key"
        verification_token = "test-verification-token"
        config = self.build_config()
        config["assertions"] = [{
            "key": "event-type",
            "name": "事件类型",
            "enabled": True,
            "source": "json_body",
            "field": "$.header.event_type",
            "operator": "p_is_equal_to",
            "expected": "contact.user.created_v3",
        }]
        config["request_decryption"] = {
            "type": "lark_event",
            "encrypt_key": encrypt_key,
            "verification_token": verification_token,
        }
        encrypted = self.encrypt_lark_event({
            "header": {
                "event_type": "contact.user.created_v3",
                "token": verification_token,
            },
        }, encrypt_key)
        request = RequestFactory().post(
            "/events",
            data=json.dumps({"encrypt": encrypted}),
            content_type="application/json",
        )
        payload = {
            "id": 1,
            "mock_key": "events",
            "method": 1,
            "path": "/",
            "record_call_log": False,
            "config": config,
        }

        result = MockRuntimeService.execute(payload, request, "/")

        self.assertTrue(result.assertion_passed)
        self.assertEqual(result.request_context.body_json["header"]["event_type"], "contact.user.created_v3")
        self.assertNotIn("encrypt", result.request_context.body_text)

    def test_runtime_rejects_lark_event_with_wrong_verification_token(self):
        encrypt_key = "test-encrypt-key"
        encrypted = self.encrypt_lark_event({"token": "wrong-token"}, encrypt_key)
        config = self.build_config()
        config["request_decryption"] = {
            "type": "lark_event",
            "encrypt_key": encrypt_key,
            "verification_token": "expected-token",
        }
        request = RequestFactory().post(
            "/events",
            data=json.dumps({"encrypt": encrypted}),
            content_type="application/json",
        )
        payload = {
            "id": 1,
            "mock_key": "events",
            "method": 1,
            "path": "/",
            "record_call_log": False,
            "config": config,
        }

        with self.assertRaises(MockRuntimeLookupError) as raised:
            MockRuntimeService.execute(payload, request, "/")

        self.assertEqual(raised.exception.code, "MOCK_VERIFICATION_TOKEN_MISMATCH")

    def test_decryption_storage_is_encrypted_and_editable_config_reveals_plaintext(self):
        stored = MockRequestDecryptionService.normalize_for_storage({
            "type": "lark_event",
            "encrypt_key": "encrypt-key",
            "verification_token": "verification-token",
        })

        self.assertNotIn("encrypt-key", json.dumps(stored))
        self.assertNotIn("verification-token", json.dumps(stored))
        self.assertEqual(MockRequestDecryptionService.editable_config(stored), {
            "type": "lark_event",
            "encrypt_key": "encrypt-key",
            "verification_token": "verification-token",
        })

        preserved = MockRequestDecryptionService.normalize_for_storage({
            "type": "lark_event",
            "encrypt_key": "",
            "verification_token": "",
        }, {"request_decryption": stored})
        self.assertEqual(preserved, stored)

    def test_path_parameters_are_extracted(self):
        self.assertEqual(
            MockRuntimeService._match_path("/groups/{group_id}/items/{item_id}", "/groups/8/items/9"),
            {"group_id": "8", "item_id": "9"},
        )

    def test_log_mapping_keeps_sensitive_header_values_without_masking(self):
        result = MockRuntimeService._truncate_mapping(
            {"Authorization": "Bearer real-token", "Cookie": "session=real-value"},
            1024,
        )
        self.assertEqual(result["Authorization"], "Bearer real-token")
        self.assertEqual(result["Cookie"], "session=real-value")

    def test_debug_reports_method_mismatch(self):
        config = SimpleNamespace(method=0, path="/items/{item_id}", config=self.build_config())
        result = MockRuntimeService.debug(config, {"method": "POST", "path": "/items/1"})
        self.assertFalse(result["method_matched"])
        self.assertTrue(result["path_matched"])

    def test_runtime_debug_call_is_always_logged_without_affecting_query(self):
        request = RequestFactory().get(
            "/items/1?__mango_mock_debug=1&source=case",
            HTTP_AUTHORIZATION="Bearer token",
        )
        payload = {
            "id": 1,
            "mock_key": "items",
            "method": 0,
            "path": "/items/{item_id}",
            "record_call_log": False,
            "config": self.build_config(),
        }

        with patch.object(MockRuntimeService, "submit_log") as submit_log:
            result = MockRuntimeService.execute(payload, request, "/items/1")
            MockRuntimeService.record_response(payload, request, result, 3)

        submit_log.assert_called_once()
        self.assertEqual(result.request_context.query, {"source": "case"})

    def test_http_duration_includes_config_loading_delay_and_response_construction(self):
        config = self.build_config()
        config["rules"][0]["response"]["delay_ms"] = 2000
        payload = {
            "id": 1, "mock_key": "items", "method": 0, "path": "/items/{item_id}",
            "enabled": True, "record_call_log": True, "config": config,
        }
        request = RequestFactory().get("/items/1", HTTP_AUTHORIZATION="Bearer test-token")
        clock = {"now": 10.0}

        def load_config(mock_key):
            clock["now"] += 0.25
            return payload

        def wait(seconds):
            clock["now"] += seconds

        def build_response(*args, **kwargs):
            clock["now"] += 0.125
            return HttpResponse(*args, **kwargs)

        with (
            patch("src.apps.auto_api.api.views.api_mock.time.monotonic", side_effect=lambda: clock["now"]),
            patch.object(MockRuntimeCache, "load", side_effect=load_config),
            patch("src.apps.auto_api.services.mock_runtime.time.sleep", side_effect=wait) as sleep,
            patch("src.apps.auto_api.api.views.api_mock.HttpResponse", side_effect=build_response),
            patch.object(MockRuntimeService, "submit_log") as submit_log,
        ):
            response = ApiMockRuntimeView()._execute(request, "items", "/items/1")

        self.assertEqual(response.status_code, 200)
        sleep.assert_called_once_with(2)
        submit_log.assert_called_once()
        self.assertEqual(submit_log.call_args.args[3], 2375)
        self.assertEqual(response["X-Mock-Trace-Id"], submit_log.call_args.args[2].trace_id)

    def test_http_success_without_recording_does_not_submit_log(self):
        payload = {
            "id": 1, "mock_key": "items", "method": 0, "path": "/items/{item_id}",
            "enabled": True, "record_call_log": False, "config": self.build_config(),
        }
        request = RequestFactory().get("/items/1", HTTP_AUTHORIZATION="Bearer test-token")
        with (
            patch.object(MockRuntimeCache, "load", return_value=payload),
            patch.object(MockRuntimeService, "submit_log") as submit_log,
        ):
            response = ApiMockRuntimeView()._execute(request, "items", "/items/1")

        self.assertEqual(response.status_code, 200)
        submit_log.assert_not_called()

    def test_http_lookup_error_duration_is_recorded_after_response_construction(self):
        payload = {"id": 1, "enabled": True}
        request = RequestFactory().get("/items/1")
        error = MockRuntimeLookupError(404, "MOCK_PATH_NOT_MATCHED", "未匹配", "test-trace")
        events = []

        def build_error(*args):
            events.append("response")
            return HttpResponse(status=404)

        def elapsed(started):
            events.append("duration")
            return 250

        with (
            patch.object(MockRuntimeCache, "load", return_value=payload),
            patch.object(MockRuntimeService, "execute", side_effect=error),
            patch.object(ApiMockRuntimeView, "_error", side_effect=build_error),
            patch.object(MockRuntimeService, "elapsed_ms_since", side_effect=elapsed),
            patch.object(MockRuntimeService, "submit_error_log") as submit_log,
        ):
            response = ApiMockRuntimeView()._execute(request, "items", "/items/1")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(events, ["response", "duration"])
        self.assertEqual(submit_log.call_args.args[-1], 250)

    def test_runtime_empty_methods_accepts_post_and_keeps_actual_method(self):
        request = RequestFactory().post(
            "/items/1",
            HTTP_AUTHORIZATION="Bearer token",
        )
        payload = {
            "id": 1,
            "mock_key": "items",
            "method": 0,
            "path": "/items/{item_id}",
            "record_call_log": False,
            "config": {**self.build_config(), "methods": []},
        }

        result = MockRuntimeService.execute(payload, request, "/items/1")

        self.assertEqual(result.request_context.method, "POST")
        self.assertTrue(result.assertion_passed)

    def test_runtime_multiple_methods_rejects_unselected_method(self):
        request = RequestFactory().put("/items/1")
        payload = {
            "id": 1,
            "mock_key": "items",
            "method": 0,
            "path": "/items/{item_id}",
            "record_call_log": False,
            "config": {**self.build_config(), "methods": [0, 1]},
        }

        with self.assertRaises(MockRuntimeLookupError) as error:
            MockRuntimeService.execute(payload, request, "/items/1")

        self.assertEqual(error.exception.status_code, 405)

    def test_debug_multiple_methods_accepts_selected_method(self):
        config_data = {**self.build_config(), "methods": [1, 6]}
        config = SimpleNamespace(method=1, path="/items/{item_id}", config=config_data)

        result = MockRuntimeService.debug(
            config,
            {
                "method": "PATCH",
                "path": "/items/1",
                "headers": {"Authorization": "Bearer token"},
            },
        )

        self.assertTrue(result["method_matched"])

    def test_runtime_replaces_response_body_and_header_for_each_call(self):
        config = self.build_config()
        config["rules"][0]["response"].update({
            "headers": {"X-Mock-Id": "${{mock_id}}"},
            "body": '{"id":"${{str_uuid()|mock_id}}"}',
        })
        payload = {
            "id": 1, "mock_key": "items", "method": 0, "path": "/items/{item_id}",
            "record_call_log": True, "config": config,
        }
        request = RequestFactory().get("/items/1")

        with patch.object(MockRuntimeService, "submit_log") as submit_log:
            first = MockRuntimeService.execute(payload, request, "/items/1")
            second = MockRuntimeService.execute(payload, request, "/items/1")
            MockRuntimeService.record_response(payload, request, first, 3)
            MockRuntimeService.record_response(payload, request, second, 3)

        first_id = json.loads(first.body)["id"]
        second_id = json.loads(second.body)["id"]
        uuid.UUID(first_id)
        uuid.UUID(second_id)
        self.assertNotEqual(first_id, second_id)
        self.assertEqual(first.headers["X-Mock-Id"], first_id)
        self.assertEqual(second.headers["X-Mock-Id"], second_id)
        self.assertEqual(submit_log.call_args_list[0].args[2].body, first.body)

    def test_runtime_rejects_unresolved_response_expression(self):
        config = self.build_config()
        config["rules"][0]["response"]["body"] = '{"id":"${{str_uuid}}"}'
        payload = {
            "id": 1, "mock_key": "items", "method": 0, "path": "/items/{item_id}",
            "record_call_log": False, "config": config,
        }

        with self.assertRaises(MockRuntimeLookupError) as raised:
            MockRuntimeService.execute(payload, RequestFactory().get("/items/1"), "/items/1")

        self.assertEqual(raised.exception.code, "MOCK_RESPONSE_TEMPLATE_ERROR")

    def test_runtime_replaces_default_text_response(self):
        config = self.build_config()
        config["default_response"].update({
            "body_type": "text",
            "content_type": "text/plain; charset=utf-8",
            "body": "mock-${{str_uuid()}}",
        })
        payload = {
            "id": 1, "mock_key": "items", "method": 0, "path": "/items/{item_id}",
            "record_call_log": False, "config": config,
        }

        result = MockRuntimeService.execute(payload, RequestFactory().get("/items/2"), "/items/2")

        self.assertIsNone(result.rule_key)
        uuid.UUID(result.body.removeprefix("mock-"))

    def test_public_request_path_contains_mock_key(self):
        self.assertEqual(
            MockRuntimeService._build_public_request_path("deded", "/"),
            "/deded",
        )
        self.assertEqual(
            MockRuntimeService._build_public_request_path("deded", "/contracts/123"),
            "/deded/contracts/123",
        )

    def test_duration_less_than_one_millisecond_is_recorded_as_one(self):
        with patch(
                "src.apps.auto_api.services.mock_runtime.time.monotonic",
                return_value=10.0004,
        ):
            self.assertEqual(MockRuntimeService.elapsed_ms_since(10.0), 1)

    def test_mock_assertion_catalog_reuses_safe_api_case_content_methods(self):
        methods = MockAssertionCatalog.method_names()

        self.assertIn("p_is_greater_than", methods)
        self.assertIn("p_is_valid_email", methods)
        self.assertNotIn("p_url_is_accessible", methods)
        self.assertNotIn("ass_func", methods)

    def test_mock_request_assertion_supports_api_case_method(self):
        request = RequestFactory().get("/items/1?count=10")
        config = self.build_config()
        config["assertions"] = [{
            "key": "count-minimum",
            "name": "数量下限",
            "enabled": True,
            "source": "query",
            "field": "count",
            "operator": "p_is_greater_than",
            "expected": "5",
        }]
        payload = {
            "id": 1,
            "mock_key": "items",
            "method": 0,
            "path": "/items/{item_id}",
            "record_call_log": False,
            "config": config,
        }

        result = MockRuntimeService.execute(payload, request, "/items/1")

        self.assertTrue(result.assertion_passed)
        self.assertEqual(result.assertion_results[0]["operator"], "p_is_greater_than")

    def test_mock_response_matcher_supports_api_case_method(self):
        request = RequestFactory().get("/items/1?count=10")
        config = self.build_config()
        config["rules"][0]["matchers"][0].update({
            "source": "query",
            "field": "count",
            "operator": "p_is_greater_than",
            "expected": "5",
        })
        payload = {
            "id": 1,
            "mock_key": "items",
            "method": 0,
            "path": "/items/{item_id}",
            "record_call_log": False,
            "config": config,
        }

        result = MockRuntimeService.execute(payload, request, "/items/1")

        self.assertEqual(result.rule_key, config["rules"][0]["key"])

    def test_validator_rejects_rule_without_matchers(self):
        value = self.build_config()
        value["rules"][0]["matchers"] = []
        with self.assertRaises(AutoApiError):
            MockConfigValidator.validate_config(value)
