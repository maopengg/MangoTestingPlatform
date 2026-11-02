import json
import re
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread
from typing import Any

import atexit
import time
from django.core.cache import cache
from django.db import DataError, IntegrityError, close_old_connections, transaction
from django.utils import timezone
from mangotools.exceptions import MangoToolsError

from src.apps.auto_api.enums import MethodEnum
from src.apps.auto_api.exceptions import (
    AutoApiError,
    MOCK_API_CONFIG_INVALID,
    MockRequestDecryptionError,
    MockRuntimeLookupError,
)
from src.apps.auto_api.models import ApiMockConfig, ApiMockRequestLog
from src.apps.auto_api.services.mock_request_decryption import MockRequestDecryptionService
from src.apps.system.services.system_config import SystemConfigService
from src.common.logging import log
from src.common.responses.json_response import extract_jsonpath_value
from src.common.testing import ObtainAssertion, ObtainTestData, assertion_func_info

MISSING = object()
MOCK_SOURCES = {"path", "query", "header", "json_body", "text_body"}
MOCK_BODY_TYPES = {"json", "text", "html", "xml", "empty"}
MOCK_MAX_ASSERTIONS = 50
MOCK_MAX_RULES = 50
MOCK_MAX_MATCHERS = 20
MOCK_MAX_CONFIG_BYTES = 4 * 1024 * 1024
MOCK_MAX_HEADER_CHARS = 16 * 1024
MOCK_MAX_RESPONSE_HEADERS = 50
MOCK_MAX_RESPONSE_HEADER_NAME_CHARS = 128
MOCK_MAX_RESPONSE_HEADER_VALUE_CHARS = 4096
MOCK_MAX_DELAY_MS = 30_000
MOCK_CACHE_TIMEOUT_SECONDS = 60
MOCK_LOCAL_CACHE_TIMEOUT_SECONDS = 1
MOCK_LOCAL_CACHE_MAX_ENTRIES = 1024
MOCK_DEBUG_QUERY_PARAM = "__mango_mock_debug"
MOCK_SUPPORTED_METHODS = frozenset({
    MethodEnum.GET.value,
    MethodEnum.POST.value,
    MethodEnum.PUT.value,
    MethodEnum.DELETE.value,
    MethodEnum.OPTIONS.value,
    MethodEnum.PATCH.value,
})
MOCK_LOG_BATCH_SIZE = 1500
MOCK_LOG_FLUSH_SECONDS = 5
MOCK_LOG_BATCH_MAX_BYTES = 4 * 1024 * 1024
MOCK_LOG_QUEUE_SIZE = 512
MOCK_LOG_CLEAR_MARKER_TIMEOUT_SECONDS = 3600
MOCK_LOG_GLOBAL_CLEAR_TIMEOUT_SECONDS = 300
MOCK_LOG_GLOBAL_CLEAR_MARKER_KEY = "mock:log:cleared:all"
MOCK_LOG_GLOBAL_WRITE_PAUSE_KEY = "mock:log:write:paused"


def mock_request_max_bytes() -> int:
    return SystemConfigService.get_ranged_int('MOCK_REQUEST_MAX_KB') * 1024


def mock_response_max_bytes() -> int:
    return SystemConfigService.get_ranged_int('MOCK_RESPONSE_MAX_KB') * 1024


def mock_log_body_max_chars() -> int:
    return SystemConfigService.get_ranged_int('MOCK_LOG_BODY_MAX_KB') * 1024


def mock_log_clear_marker_key(config_id: int) -> str:
    return f"mock:log:cleared:{config_id}"


class MockLogBatchWriter:
    def __init__(self, *, batch_size=MOCK_LOG_BATCH_SIZE, flush_seconds=MOCK_LOG_FLUSH_SECONDS,
                 max_batch_bytes=MOCK_LOG_BATCH_MAX_BYTES, queue_size=MOCK_LOG_QUEUE_SIZE):
        self.batch_size = batch_size
        self.flush_seconds = flush_seconds
        self.max_batch_bytes = max_batch_bytes
        self._queue = Queue(maxsize=queue_size)
        self._stop = Event()
        self._start_lock = Lock()
        self._thread = None

    def submit(self, payload: dict):
        if self._stop.is_set():
            self._write_batch([payload])
            return
        self._ensure_started()
        try:
            self._queue.put_nowait((time.monotonic(), payload))
        except Full:
            # 背压发生时由请求线程写入，避免无界占用内存或静默丢失日志。
            self._write_batch([payload])

    def _ensure_started(self):
        if self._thread is not None:
            return
        with self._start_lock:
            if self._thread is None:
                self._thread = Thread(target=self._run, name="api-mock-log-batch", daemon=True)
                self._thread.start()

    def _run(self):
        batch = []
        batch_bytes = 0
        deadline = None
        while True:
            if batch and (time.monotonic() >= deadline or (self._stop.is_set() and self._queue.empty())):
                self._write_batch(batch)
                batch, batch_bytes, deadline = [], 0, None
            if self._stop.is_set() and self._queue.empty():
                return
            timeout = max(deadline - time.monotonic(), 0) if deadline else 0.5
            try:
                queued_at, payload = self._queue.get(timeout=timeout)
            except Empty:
                continue
            payload_bytes = len(json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"))
            if batch and batch_bytes + payload_bytes > self.max_batch_bytes:
                self._write_batch(batch)
                batch, batch_bytes, deadline = [], 0, None
            if not batch:
                deadline = queued_at + self.flush_seconds
            batch.append(payload)
            batch_bytes += payload_bytes
            if len(batch) >= self.batch_size or batch_bytes >= self.max_batch_bytes:
                self._write_batch(batch)
                batch, batch_bytes, deadline = [], 0, None

    def close(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
            if self._thread.is_alive():
                log.system.error("Mock调用记录退出刷盘超时，仍有未完成日志")

    @staticmethod
    def _write_batch(payloads: list[dict]):
        close_old_connections()
        eligible_payloads = []
        try:
            with transaction.atomic():
                config_ids = sorted({payload["mock_config_id"] for payload in payloads})
                list(
                    ApiMockConfig.objects.select_for_update()
                    .filter(id__in=config_ids)
                    .order_by("id")
                    .values_list("id", flat=True)
                )
                marker_keys = [mock_log_clear_marker_key(config_id) for config_id in config_ids]
                try:
                    markers = cache.get_many([
                        *marker_keys,
                        MOCK_LOG_GLOBAL_CLEAR_MARKER_KEY,
                        MOCK_LOG_GLOBAL_WRITE_PAUSE_KEY,
                    ])
                except Exception as error:
                    log.system.error(f"Mock调用记录清空标记读取失败：{error}")
                    markers = {}
                if markers.get(MOCK_LOG_GLOBAL_WRITE_PAUSE_KEY):
                    return
                global_marker = markers.get(MOCK_LOG_GLOBAL_CLEAR_MARKER_KEY)
                eligible_payloads = [
                    payload for payload in payloads
                    if (
                            (global_marker is None or payload["create_time"] > global_marker)
                            and (
                                    (marker := markers.get(
                                        mock_log_clear_marker_key(payload["mock_config_id"]))) is None
                                    or payload["create_time"] > marker
                            )
                    )
                ]
                if eligible_payloads:
                    ApiMockRequestLog.objects.bulk_create(
                        [ApiMockRequestLog(**payload) for payload in eligible_payloads],
                        batch_size=MOCK_LOG_BATCH_SIZE,
                    )
        except (DataError, IntegrityError) as error:
            log.system.error(f"Mock调用记录批量写入失败，改为逐条重试：count={len(eligible_payloads)}, error={error}")
            for payload in eligible_payloads:
                try:
                    with transaction.atomic():
                        config_id = payload["mock_config_id"]
                        ApiMockConfig.objects.select_for_update().get(pk=config_id)
                        markers = cache.get_many([
                            mock_log_clear_marker_key(config_id),
                            MOCK_LOG_GLOBAL_CLEAR_MARKER_KEY,
                            MOCK_LOG_GLOBAL_WRITE_PAUSE_KEY,
                        ])
                        marker = markers.get(mock_log_clear_marker_key(config_id))
                        global_marker = markers.get(MOCK_LOG_GLOBAL_CLEAR_MARKER_KEY)
                        if (
                                not markers.get(MOCK_LOG_GLOBAL_WRITE_PAUSE_KEY)
                                and (global_marker is None or payload["create_time"] > global_marker)
                                and (marker is None or payload["create_time"] > marker)
                        ):
                            ApiMockRequestLog.objects.create(**payload)
                except Exception as item_error:
                    log.system.error(f"Mock调用记录写入失败：trace_id={payload.get('trace_id')}, error={item_error}")
        except Exception as error:
            log.system.error(f"Mock调用记录批量写入失败：count={len(payloads)}, error={error}")
        finally:
            close_old_connections()


_log_batch_writer = MockLogBatchWriter()
atexit.register(_log_batch_writer.close)


class MockAssertionCatalog:
    """Expose API Case content assertions that are safe for synchronous Mock requests."""

    SOURCE_GROUP = "内容断言"
    EXCLUDED_CLASSES = {"URL断言"}

    @classmethod
    def catalog(cls) -> list[dict]:
        result = []
        for group in assertion_func_info:
            if not isinstance(group, dict) or group.get("value") != cls.SOURCE_GROUP:
                continue
            for method_class in group.get("children") or []:
                if not isinstance(method_class, dict) or method_class.get("value") in cls.EXCLUDED_CLASSES:
                    continue
                methods = []
                for method in method_class.get("children") or []:
                    parameters = method.get("parameter") or []
                    fields = {
                        str(parameter.get("f") or "")
                        for parameter in parameters
                        if isinstance(parameter, dict)
                    }
                    method_name = str(method.get("value") or "").strip()
                    if not method_name or "actual" not in fields or not fields.issubset({"actual", "expect"}):
                        continue
                    methods.append({
                        "label": method.get("label") or method_name,
                        "value": method_name,
                        "requires_expected": "expect" in fields,
                    })
                if methods:
                    result.append({
                        "label": method_class.get("label") or method_class.get("value"),
                        "value": method_class.get("value"),
                        "children": methods,
                    })
        return result

    @classmethod
    @lru_cache(maxsize=1)
    def method_names(cls) -> frozenset[str]:
        return frozenset({
            method["value"]
            for method_class in cls.catalog()
            for method in method_class["children"]
        })


@dataclass(frozen=True)
class MockRequestContext:
    method: str
    path: str
    path_values: dict[str, str]
    query: dict[str, Any]
    headers: dict[str, Any]
    body_text: str
    body_json: Any
    body_json_error: str = ""


@dataclass(frozen=True)
class MockRuntimeResult:
    status_code: int
    content_type: str
    headers: dict[str, str]
    body: str
    delay_ms: int
    trace_id: str
    rule_key: str | None
    assertion_passed: bool
    assertion_results: list[dict]
    request_context: MockRequestContext
    callback_log_id: int | None = None


class MockConfigValidator:
    MOCK_KEY_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    PATH_PARAM_PATTERN = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")

    @classmethod
    def validate_mock_key(cls, value: str) -> str:
        value = str(value or "").strip()
        if not cls.MOCK_KEY_PATTERN.fullmatch(value):
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=("Mock URL标识只能包含小写字母、数字和连字符",))
        return value

    @classmethod
    def validate_path(cls, value: str) -> str:
        value = str(value or "").strip()
        if not value.startswith("/"):
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=("请求路径必须以 / 开头",))
        names = cls.PATH_PARAM_PATTERN.findall(value)
        if len(names) != len(set(names)):
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=("请求路径中的Path参数名称不允许重复",))
        if "{" in cls.PATH_PARAM_PATTERN.sub("", value) or "}" in cls.PATH_PARAM_PATTERN.sub("", value):
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=("请求路径中的Path参数格式不正确",))
        return value

    @classmethod
    def validate_config(cls, value: Any) -> dict:
        if not isinstance(value, dict):
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=("配置必须是JSON对象",))
        if len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")) > MOCK_MAX_CONFIG_BYTES:
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=("Mock完整配置不能超过4MB",))
        assertions = value.get("assertions", [])
        rules = value.get("rules", [])
        default_response = value.get("default_response")
        request_decryption = value.get("request_decryption") or {"type": "none"}
        methods = value.get("methods")
        if methods is not None:
            if not isinstance(methods, list) or any(
                    not isinstance(method, int) or method not in MOCK_SUPPORTED_METHODS
                    for method in methods
            ):
                raise AutoApiError(MOCK_API_CONFIG_INVALID, value=("请求方法配置不合法",))
            if len(methods) != len(set(methods)):
                raise AutoApiError(MOCK_API_CONFIG_INVALID, value=("请求方法不允许重复",))
        if not isinstance(assertions, list) or len(assertions) > MOCK_MAX_ASSERTIONS:
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"请求断言最多{MOCK_MAX_ASSERTIONS}条",))
        if not isinstance(rules, list) or len(rules) > MOCK_MAX_RULES:
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"响应规则最多{MOCK_MAX_RULES}条",))
        if not isinstance(default_response, dict):
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=("必须配置默认响应",))
        if not isinstance(request_decryption, dict) or request_decryption.get("type", "none") not in {
            MockRequestDecryptionService.TYPE_NONE,
            MockRequestDecryptionService.TYPE_LARK_EVENT,
        }:
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=("请求解密配置不合法",))

        cls._validate_conditions(assertions, "请求断言")
        rule_keys = set()
        for index, rule in enumerate(rules, start=1):
            if not isinstance(rule, dict):
                raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"第{index}条响应规则必须是JSON对象",))
            key = str(rule.get("key") or "").strip()
            if not key or key in rule_keys:
                raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"第{index}条响应规则Key为空或重复",))
            rule_keys.add(key)
            matchers = rule.get("matchers", [])
            if not isinstance(matchers, list) or not matchers or len(matchers) > MOCK_MAX_MATCHERS:
                raise AutoApiError(MOCK_API_CONFIG_INVALID,
                                   value=(f"单条响应规则需配置1到{MOCK_MAX_MATCHERS}个匹配条件",),
                                   )
            if not any(item.get("enabled", True) for item in matchers if isinstance(item, dict)):
                raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"响应规则【{key}】至少启用一个匹配条件",))
            cls._validate_conditions(matchers, f"响应规则【{key}】匹配条件")
            cls._validate_response(rule.get("response"), f"响应规则【{key}】")
            for matcher in matchers:
                matcher.pop("message", None)
        cls._validate_response(default_response, "默认响应")
        for assertion in assertions:
            assertion.pop("message", None)
        return {
            "methods": methods,
            "assertions": assertions,
            "rules": rules,
            "default_response": default_response,
            "request_decryption": request_decryption,
        }

    @classmethod
    def _validate_conditions(cls, items: list, label: str):
        keys = set()
        allowed_operators = MockAssertionCatalog.method_names()
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"{label}第{index}项必须是JSON对象",))
            key = str(item.get("key") or "").strip()
            if not key or key in keys:
                raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"{label}第{index}项Key为空或重复",))
            keys.add(key)
            if item.get("source") not in MOCK_SOURCES:
                raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"{label}第{index}项数据来源不支持",))
            if item.get("operator") not in allowed_operators:
                raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"{label}第{index}项操作符不支持",))
            if item.get("source") != "text_body" and not str(item.get("field") or "").strip():
                raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"{label}第{index}项字段不允许为空",))

    @staticmethod
    def _validate_response(response: Any, label: str):
        if not isinstance(response, dict):
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"{label}缺少响应配置",))
        try:
            status_code = int(response.get("status_code"))
            delay_ms = int(response.get("delay_ms") or 0)
        except (TypeError, ValueError) as error:
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"{label}状态码或延迟格式不正确",)) from error
        if not 100 <= status_code <= 599:
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"{label}状态码必须在100到599之间",))
        if not 0 <= delay_ms <= MOCK_MAX_DELAY_MS:
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"{label}延迟必须在0到{MOCK_MAX_DELAY_MS}毫秒之间",))
        body_type = str(response.get("body_type") or "json")
        if body_type not in MOCK_BODY_TYPES:
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"{label}响应类型不支持",))
        body = "" if body_type == "empty" else str(response.get("body") or "")
        max_bytes = mock_response_max_bytes()
        if len(body.encode("utf-8")) > max_bytes:
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"{label}响应体不能超过{max_bytes // 1024}KB",))
        if body_type == "json":
            try:
                json.loads(body)
            except (TypeError, ValueError) as error:
                raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"{label}响应体不是合法JSON",)) from error
        headers = response.get("headers") or {}
        if not isinstance(headers, dict):
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"{label}响应头必须是JSON对象",))
        if len(headers) > MOCK_MAX_RESPONSE_HEADERS:
            raise AutoApiError(MOCK_API_CONFIG_INVALID,
                               value=(f"{label}响应头最多{MOCK_MAX_RESPONSE_HEADERS}项",),
                               )
        forbidden = {"content-length", "transfer-encoding"}
        for key, value in headers.items():
            key_text = str(key)
            value_text = str(value)
            if key_text.lower() in forbidden:
                raise AutoApiError(MOCK_API_CONFIG_INVALID,
                                   value=(f"{label}不能配置Content-Length或Transfer-Encoding",))
            if not key_text or len(key_text) > MOCK_MAX_RESPONSE_HEADER_NAME_CHARS:
                raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"{label}响应头名称长度不合法",))
            if len(value_text) > MOCK_MAX_RESPONSE_HEADER_VALUE_CHARS:
                raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"{label}响应头值过长",))
            if "\r" in key_text or "\n" in key_text or "\r" in value_text or "\n" in value_text:
                raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"{label}响应头不允许包含换行符",))
        content_type = str(response.get("content_type") or "")
        if len(content_type) > 256 or "\r" in content_type or "\n" in content_type:
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(f"{label}Content-Type不合法",))


class MockRuntimeCache:
    _local_entries: OrderedDict[str, tuple[float, dict]] = OrderedDict()
    _local_lock = Lock()

    @staticmethod
    def key(mock_key: str) -> str:
        return f"mock:runtime:{mock_key}"

    @classmethod
    def invalidate(cls, mock_key: str):
        with cls._local_lock:
            cls._local_entries.pop(mock_key, None)
        try:
            cache.delete(cls.key(mock_key))
        except Exception as error:
            log.system.error(f"Mock运行缓存清理失败：mock_key={mock_key}, error={error}")

    @classmethod
    def load(cls, mock_key: str) -> dict | None:
        now = time.monotonic()
        with cls._local_lock:
            entry = cls._local_entries.get(mock_key)
            if entry is not None:
                if entry[0] > now:
                    cls._local_entries.move_to_end(mock_key)
                    return entry[1]
                del cls._local_entries[mock_key]
        cache_key = cls.key(mock_key)
        try:
            payload = cache.get(cache_key)
        except Exception as error:
            log.system.error(f"Mock运行缓存读取失败，已回源数据库：mock_key={mock_key}, error={error}")
            payload = None
        if payload is None:
            config = ApiMockConfig.objects.filter(mock_key=mock_key).first()
            if config is None:
                return None
            payload = {
                "id": config.id,
                "mock_key": config.mock_key,
                "method": config.method,
                "path": config.path,
                "enabled": config.enabled,
                "record_call_log": config.record_call_log,
                "config": config.config,
            }
            try:
                cache.set(cache_key, payload, MOCK_CACHE_TIMEOUT_SECONDS)
            except Exception as error:
                log.system.error(f"Mock运行缓存写入失败：mock_key={mock_key}, error={error}")
        runtime_payload = payload
        decryption = ((payload.get("config") or {}).get("request_decryption") or {})
        if decryption.get("type") == MockRequestDecryptionService.TYPE_LARK_EVENT:
            runtime_payload = dict(payload)
            runtime_payload["config"] = MockRequestDecryptionService.runtime_config(payload.get("config"))
        with cls._local_lock:
            cls._local_entries[mock_key] = (time.monotonic() + MOCK_LOCAL_CACHE_TIMEOUT_SECONDS, runtime_payload)
            cls._local_entries.move_to_end(mock_key)
            if len(cls._local_entries) > MOCK_LOCAL_CACHE_MAX_ENTRIES:
                cls._local_entries.popitem(last=False)
        return runtime_payload


class MockRuntimeService:
    METHOD_BY_NAME = {name: value for value, name in MethodEnum.obj().items()}
    CONTENT_TYPES = {
        "json": "application/json",
        "text": "text/plain; charset=utf-8",
        "html": "text/html; charset=utf-8",
        "xml": "application/xml; charset=utf-8",
        "empty": "text/plain; charset=utf-8",
    }

    @classmethod
    def configured_methods(cls, payload: dict) -> list[int]:
        config = payload.get("config") or {}
        if "methods" in config:
            return config.get("methods") or []
        return [payload["method"]]

    @classmethod
    def method_matches(cls, payload: dict, method: str) -> bool:
        methods = cls.configured_methods(payload)
        if not methods:
            return True
        method_value = cls.METHOD_BY_NAME.get(method.upper())
        return method_value in methods

    @classmethod
    def execute(cls, payload: dict, request, remaining_path: str, *, observe_callback=True) -> MockRuntimeResult:
        trace_id = f"mock_{uuid.uuid4().hex}"
        path_values = cls._match_path(payload["path"], remaining_path)
        if path_values is None:
            raise MockRuntimeLookupError(404, "MOCK_PATH_NOT_MATCHED", "请求路径未匹配Mock配置", trace_id)
        if not cls.method_matches(payload, request.method):
            raise MockRuntimeLookupError(405, "MOCK_METHOD_NOT_ALLOWED", "请求方法不匹配Mock配置", trace_id)
        if observe_callback:
            from src.apps.auto_api.services.callback import ApiCallbackService
            observed = ApiCallbackService.intercept(payload, request, remaining_path)
            if observed is not None:
                return observed
        config = payload.get("config") or {}
        context = cls._build_request_context(
            request,
            remaining_path,
            path_values,
            config.get("request_decryption"),
            trace_id,
        )
        assertion_results = [
            cls._evaluate_condition(item, context, assertion=True)
            for item in config.get("assertions", [])
            if item.get("enabled", True)
        ]
        assertion_passed = all(item["passed"] for item in assertion_results)

        matched_rule = None
        for rule in config.get("rules", []):
            if not rule.get("enabled", True):
                continue
            matcher_results = [
                cls._evaluate_condition(item, context, assertion=False)
                for item in rule.get("matchers", [])
                if item.get("enabled", True)
            ]
            if all(item["passed"] for item in matcher_results):
                matched_rule = rule
                break
        response = (matched_rule or {}).get("response") or config.get("default_response") or {}
        body_type = response.get("body_type") or "json"
        headers, body = cls._render_response(response, body_type, trace_id)
        result = MockRuntimeResult(
            status_code=int(response.get("status_code") or 200),
            content_type=str(response.get("content_type") or cls.CONTENT_TYPES.get(body_type, "text/plain")),
            headers=headers,
            body=body,
            delay_ms=int(response.get("delay_ms") or 0),
            trace_id=trace_id,
            rule_key=(matched_rule or {}).get("key"),
            assertion_passed=assertion_passed,
            assertion_results=assertion_results,
            request_context=context,
        )
        if result.delay_ms:
            time.sleep(result.delay_ms / 1000)
        return result

    @classmethod
    def record_response(cls, payload: dict, request, result: MockRuntimeResult, duration_ms: int):
        """响应构造完成后记录耗时，避免漏计配置读取和 HTTP 响应构造。"""
        if result.callback_log_id is not None:
            ApiMockRequestLog.objects.filter(pk=result.callback_log_id).update(duration_ms=duration_ms)
            return
        if (
                payload.get("record_call_log") or
                not result.assertion_passed or
                request.GET.get(MOCK_DEBUG_QUERY_PARAM) == "1"
        ):
            cls.submit_log(
                payload["id"],
                payload["mock_key"],
                result,
                duration_ms,
                request,
            )

    @staticmethod
    def _render_response(response: dict, body_type: str, trace_id: str) -> tuple[dict[str, str], str]:
        configured_body = "" if body_type == "empty" else str(response.get("body") or "")
        configured_headers = {str(key): str(value) for key, value in (response.get("headers") or {}).items()}
        if "${{" not in configured_body and not any("${{" in value for value in configured_headers.values()):
            return configured_headers, configured_body

        test_data = ObtainTestData()
        try:
            rendered_body = test_data.replace(configured_body) if "${{" in configured_body else configured_body
            if isinstance(rendered_body, str):
                body = rendered_body
            elif body_type == "json":
                body = json.dumps(rendered_body, ensure_ascii=False)
            else:
                body = "" if rendered_body is None else str(rendered_body)
            headers = {
                key: str(test_data.replace(value)) if "${{" in value else value
                for key, value in configured_headers.items()
            }
        except MangoToolsError as error:
            raise MockRuntimeLookupError(
                500, "MOCK_RESPONSE_TEMPLATE_ERROR", "Mock响应模板解析失败，请检查表达式", trace_id,
            ) from error
        max_bytes = mock_response_max_bytes()
        if len(body.encode("utf-8")) > max_bytes:
            raise MockRuntimeLookupError(500, "MOCK_RESPONSE_TOO_LARGE", f"Mock响应体超过{max_bytes // 1024}KB限制",
                                         trace_id)
        if body_type == "json":
            try:
                json.loads(body)
            except (TypeError, ValueError) as error:
                raise MockRuntimeLookupError(
                    500, "MOCK_RESPONSE_TEMPLATE_ERROR", "Mock响应模板解析后不是合法JSON", trace_id,
                ) from error
        for value in headers.values():
            if len(value) > MOCK_MAX_RESPONSE_HEADER_VALUE_CHARS or "\r" in value or "\n" in value:
                raise MockRuntimeLookupError(
                    500, "MOCK_RESPONSE_TEMPLATE_ERROR", "Mock响应模板生成的响应头不合法", trace_id,
                )
        return headers, body

    @classmethod
    def debug(cls, config: ApiMockConfig, request_data: dict) -> dict:
        method = str(request_data.get("method") or MethodEnum.obj().get(config.method) or "GET").upper()
        method_matched = cls.method_matches(
            {"method": config.method, "config": config.config or {}},
            method,
        )
        path = str(request_data.get("path") or config.path)
        path_values = cls._match_path(config.path, path)
        if path_values is None or not method_matched:
            return {
                "method_matched": method_matched,
                "path_matched": path_values is not None,
                "assertion_passed": False,
                "assertion_results": [],
                "matched_rule_key": None,
                "used_default_response": False,
                "response_preview": None,
            }
        runtime_config = MockRequestDecryptionService.runtime_config(config.config or {})
        raw_body = request_data.get("body")
        body_text = raw_body if isinstance(raw_body, str) else json.dumps(raw_body,
                                                                          ensure_ascii=False) if raw_body is not None else ""
        body_text, body_json, body_error = cls._prepare_body(
            body_text,
            runtime_config.get("request_decryption"),
            f"mock_{uuid.uuid4().hex}",
        )
        context = MockRequestContext(
            method=method,
            path=path,
            path_values=path_values,
            query=request_data.get("query") or {},
            headers=request_data.get("headers") or {},
            body_text=body_text,
            body_json=body_json,
            body_json_error=body_error,
        )
        assertions = [
            cls._evaluate_condition(item, context, assertion=True)
            for item in runtime_config.get("assertions", [])
            if item.get("enabled", True)
        ]
        matched_rule = None
        matcher_results = []
        for rule in runtime_config.get("rules", []):
            if not rule.get("enabled", True):
                continue
            current = [
                cls._evaluate_condition(item, context, assertion=False)
                for item in rule.get("matchers", [])
                if item.get("enabled", True)
            ]
            matcher_results.append(
                {"rule_key": rule.get("key"), "results": current, "matched": all(i["passed"] for i in current)})
            if all(item["passed"] for item in current):
                matched_rule = rule
                break
        response = (matched_rule or {}).get("response") or runtime_config.get("default_response")
        return {
            "method_matched": True,
            "path_matched": True,
            "assertion_passed": all(item["passed"] for item in assertions),
            "assertion_results": assertions,
            "matcher_results": matcher_results,
            "matched_rule_key": (matched_rule or {}).get("key"),
            "used_default_response": matched_rule is None,
            "response_preview": response,
        }

    @classmethod
    def _build_request_context(
            cls,
            request,
            path: str,
            path_values: dict,
            request_decryption: dict | None = None,
            trace_id: str | None = None,
    ) -> MockRequestContext:
        max_bytes = mock_request_max_bytes()
        if len(request.body or b"") > max_bytes:
            raise MockRuntimeLookupError(413, "MOCK_REQUEST_TOO_LARGE", f"请求体超过{max_bytes // 1024}KB限制",
                                         f"mock_{uuid.uuid4().hex}")
        body_text = (request.body or b"").decode("utf-8", errors="replace")
        body_text, body_json, body_error = cls._prepare_body(
            body_text,
            request_decryption,
            trace_id or f"mock_{uuid.uuid4().hex}",
        )
        query = {
            key: values if len(values) > 1 else values[0]
            for key, values in request.GET.lists()
            if key != MOCK_DEBUG_QUERY_PARAM
        }
        headers = {str(key): value for key, value in request.headers.items()}
        return MockRequestContext(
            method=request.method.upper(),
            path=path,
            path_values=path_values,
            query=query,
            headers=headers,
            body_text=body_text,
            body_json=body_json,
            body_json_error=body_error,
        )

    @classmethod
    def _prepare_body(
            cls,
            body_text: str,
            request_decryption: dict | None,
            trace_id: str,
    ) -> tuple[str, Any, str]:
        try:
            decrypted_text, decrypted_json = MockRequestDecryptionService.decrypt_body(
                body_text,
                request_decryption,
            )
        except MockRequestDecryptionError as error:
            raise MockRuntimeLookupError(400, error.code, error.message, trace_id) from error
        if (request_decryption or {}).get("type") == MockRequestDecryptionService.TYPE_LARK_EVENT:
            return decrypted_text, decrypted_json, ""
        body_json, body_error = cls._parse_json(body_text)
        return body_text, body_json, body_error

    @staticmethod
    def _parse_json(body_text: str) -> tuple[Any, str]:
        if not body_text:
            return None, ""
        try:
            return json.loads(body_text), ""
        except (TypeError, ValueError) as error:
            return None, str(error)

    @classmethod
    def _match_path(cls, template: str, actual_path: str) -> dict[str, str] | None:
        pattern_parts = []
        cursor = 0
        for match in MockConfigValidator.PATH_PARAM_PATTERN.finditer(template):
            pattern_parts.append(re.escape(template[cursor:match.start()]))
            pattern_parts.append(f"(?P<{match.group(1)}>[^/]+)")
            cursor = match.end()
        pattern_parts.append(re.escape(template[cursor:]))
        matched = re.fullmatch("".join(pattern_parts), actual_path)
        return matched.groupdict() if matched else None

    @classmethod
    def _evaluate_condition(cls, item: dict, context: MockRequestContext, *, assertion: bool) -> dict:
        actual, extraction_error = cls._extract_value(item, context)
        operator = item.get("operator")
        expected = item.get("expected")
        passed = False
        error = extraction_error
        if not error:
            try:
                if operator in MockAssertionCatalog.method_names():
                    if actual is MISSING:
                        error = "请求字段不存在"
                    else:
                        ObtainAssertion().ass(
                            method=operator,
                            actual=actual,
                            expect=cls._normalize_assertion_value(expected),
                        )
                        passed = True
            except (AssertionError, TypeError, ValueError, re.error) as condition_error:
                error = str(condition_error)
                passed = False
        message = "" if passed else str(error or "请求值不符合预期")
        return {
            "key": item.get("key"),
            "name": item.get("name") or item.get("key"),
            "source": item.get("source"),
            "field": item.get("field") or "",
            "operator": operator,
            "passed": passed,
            "actual": cls._preview_value(None if actual is MISSING else actual),
            "expected": cls._preview_value(expected),
            "message": message if assertion or not passed else "",
        }

    @staticmethod
    def _normalize_assertion_value(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        text = value.strip()
        if not text or text[0] not in "[{":
            return value
        try:
            return json.loads(text)
        except (TypeError, ValueError):
            return value

    @staticmethod
    def _extract_value(item: dict, context: MockRequestContext) -> tuple[Any, str]:
        source = item.get("source")
        field = str(item.get("field") or "")
        if source == "path":
            return context.path_values.get(field, MISSING), ""
        if source == "query":
            return context.query.get(field, MISSING), ""
        if source == "header":
            lowered = {str(key).lower(): value for key, value in context.headers.items()}
            return lowered.get(field.lower(), MISSING), ""
        if source == "text_body":
            return context.body_text, ""
        if source == "json_body":
            if context.body_json_error:
                return MISSING, "请求体不是合法JSON"
            if context.body_json is None:
                return MISSING, "请求体为空"
            try:
                return extract_jsonpath_value(
                    context.body_json,
                    field,
                    operation="Mock请求参数提取",
                ), ""
            except AutoApiError as error:
                return MISSING, error.msg
        return MISSING, "不支持的数据来源"

    @staticmethod
    def _preview_value(value: Any) -> Any:
        if isinstance(value, str):
            return value[:2000]
        if isinstance(value, (dict, list)):
            text = json.dumps(value, ensure_ascii=False, default=str)
            return text[:2000]
        return value

    @classmethod
    def submit_log(
            cls,
            mock_config_id: int,
            mock_key: str,
            result: MockRuntimeResult,
            duration_ms: int,
            request,
    ):
        context = result.request_context
        request_data = {
            "query": cls._truncate_mapping(context.query, MOCK_MAX_HEADER_CHARS),
            "headers": cls._truncate_mapping(context.headers, MOCK_MAX_HEADER_CHARS),
            "body": context.body_text[:mock_log_body_max_chars()],
        }
        response_data = {
            "headers": result.headers,
            "body": result.body[:mock_log_body_max_chars()],
            "content_type": result.content_type,
        }
        payload = {
            "create_time": timezone.now(),
            "mock_config_id": mock_config_id,
            "trace_id": result.trace_id,
            "rule_key": result.rule_key,
            "method": cls.METHOD_BY_NAME.get(context.method, MethodEnum.GET.value),
            "request_path": cls._build_public_request_path(mock_key, context.path)[:1024],
            "request_data": request_data,
            "assertion_passed": result.assertion_passed,
            "assertion_results": result.assertion_results,
            "response_status": result.status_code,
            "response_data": response_data,
            "duration_ms": duration_ms,
            "client_ip": request.META.get("REMOTE_ADDR") or None,
        }
        cls._submit_log_payload(payload)

    @classmethod
    def submit_error_log(
            cls,
            config_payload: dict,
            request,
            remaining_path: str,
            trace_id: str,
            status_code: int,
            error_message: str,
            duration_ms: int,
    ):
        """强制记录未进入正常响应链路的请求；请求内容保留原值，仅做长度截断。"""
        try:
            raw_body = (request.body or b"")[:mock_log_body_max_chars()]
            body_text = raw_body.decode("utf-8", errors="replace")
            query = {
                key: values if len(values) > 1 else values[0]
                for key, values in request.GET.lists()
                if key != MOCK_DEBUG_QUERY_PARAM
            }
            request_data = {
                "query": cls._truncate_mapping(query, MOCK_MAX_HEADER_CHARS),
                "headers": cls._truncate_mapping(
                    {str(key): value for key, value in request.headers.items()},
                    MOCK_MAX_HEADER_CHARS,
                ),
                "body": body_text,
            }
            payload = {
                "create_time": timezone.now(),
                "mock_config_id": config_payload["id"],
                "trace_id": trace_id,
                "method": cls.METHOD_BY_NAME.get(request.method.upper(), MethodEnum.GET.value),
                "request_path": cls._build_public_request_path(
                    config_payload.get("mock_key") or "",
                    remaining_path,
                )[:1024],
                "request_data": request_data,
                "assertion_passed": True,
                "assertion_results": [],
                "response_status": status_code,
                "response_data": {},
                "duration_ms": max(int(duration_ms), 1),
                "error_message": str(error_message)[:1000],
                "client_ip": request.META.get("REMOTE_ADDR") or None,
            }
            cls._submit_log_payload(payload)
        except Exception as error:
            log.system.error(
                f"Mock异常调用记录构造失败：trace_id={trace_id}, error={error}"
            )

    @staticmethod
    def _build_public_request_path(mock_key: str, remaining_path: str) -> str:
        """保存 /api/mock 前缀之后的业务请求路径。"""
        normalized_key = str(mock_key or "").strip("/")
        normalized_path = str(remaining_path or "/")
        if not normalized_path.startswith("/"):
            normalized_path = f"/{normalized_path}"
        if not normalized_key:
            return normalized_path
        if normalized_path == "/":
            return f"/{normalized_key}"
        return f"/{normalized_key}{normalized_path}"

    @staticmethod
    def elapsed_ms_since(started: float) -> int:
        return max(int((time.monotonic() - started) * 1000), 1)

    @staticmethod
    def _truncate_mapping(value: dict, limit: int) -> dict:
        result = {}
        used = 0
        for key, item in value.items():
            text = str(item)
            remaining = max(limit - used, 0)
            if remaining <= 0:
                break
            result[str(key)] = text[:remaining]
            used += len(str(key)) + len(result[str(key)])
        return result

    @classmethod
    def _submit_log_payload(cls, payload: dict):
        _log_batch_writer.submit(payload)
