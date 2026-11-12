import csv
import json
import tempfile
import uuid
from urllib.parse import quote

import time
from django.http import FileResponse, HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.api.serializers.api_mock import ApiMockConfigSerializer, ApiMockConfigListSerializer, \
    ApiMockRequestLogSerializer
from src.apps.auto_api.enums import MethodEnum
from src.apps.auto_api.exceptions import (
    AutoApiError,
    MOCK_API_USER_CONFIG_UPDATE_CONFLICT,
    MOCK_API_API_INFO_NOT_FOUND,
)
from src.apps.auto_api.exceptions import MockRequestDecryptionError, MockRuntimeLookupError
from src.apps.auto_api.models import ApiMockConfig, ApiMockRequestLog
from src.apps.auto_api.services.mock.mock_log_cleanup import MockRequestLogCleanupService
from src.apps.auto_api.services.mock.mock_runtime import MockAssertionCatalog, MockRuntimeCache, MockRuntimeService
from src.common.decorators.error_response import error_response
from src.common.exceptions import RESOURCE_ACCESS_DENIED
from src.common.logging import log
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0005,
    RESPONSE_MSG_0082,
    RESPONSE_MSG_0158,
    RESPONSE_MSG_0210,
)
from src.common.responses.update_audit import ApiUpdateUserCRUDMixin, save_update_user


class ApiMockConfigCRUD(ApiUpdateUserCRUDMixin, ModelCRUD):
    model = ApiMockConfig
    queryset = ApiMockConfig.objects.all()
    serializer_class = ApiMockConfigListSerializer
    serializer = ApiMockConfigSerializer
    page_permission_key = "api.mock"
    not_matching_str = ModelCRUD.not_matching_str + ["update_user", "record_call_log", "enabled", "method"]

    def post(self, request: Request):
        """新增Mock 配置"""
        response = super().post(request)
        if getattr(response, "data", {}).get("code") == 200:
            MockRuntimeCache.invalidate(request.data.get("mock_key"))
        return response

    def put(self, request: Request):
        """修改Mock 配置"""
        instance = self.model.objects.filter(id=request.data.get("id")).first()
        if instance is None:
            return ResponseData.fail(RESPONSE_MSG_0158)
        client_update_time = parse_datetime(str(request.data.get("update_time") or ""))
        if client_update_time is not None:
            current = instance.update_time.replace(microsecond=0)
            candidate = client_update_time.replace(microsecond=0)
            if current.tzinfo is not None and candidate.tzinfo is None:
                candidate = candidate.replace(tzinfo=current.tzinfo)
            if current != candidate:
                raise AutoApiError(MOCK_API_USER_CONFIG_UPDATE_CONFLICT)
        old_key = instance.mock_key
        response = super().put(request)
        if getattr(response, "data", {}).get("code") == 200:
            MockRuntimeCache.invalidate(old_key)
            new_key = request.data.get("mock_key")
            if new_key and new_key != old_key:
                MockRuntimeCache.invalidate(new_key)
        return response

    def delete(self, request: Request):
        """删除Mock 配置"""
        ids = request.query_params.getlist("id[]")
        if request.query_params.get("id"):
            ids.append(request.query_params.get("id"))
        keys = list(self.model.objects.filter(id__in=ids).values_list("mock_key", flat=True))
        response = super().delete(request)
        if getattr(response, "data", {}).get("code") == 200:
            for key in keys:
                MockRuntimeCache.invalidate(key)
        return response


class ApiMockConfigViews(ViewSet):
    model = ApiMockConfig
    serializer_class = ApiMockConfigSerializer

    def _get_config(self, request: Request) -> ApiMockConfig:
        config = self.model.objects.filter(id=request.query_params.get("id") or request.data.get("id")).first()
        if config is None:
            raise AutoApiError(MOCK_API_API_INFO_NOT_FOUND)
        helper = ApiMockConfigCRUD()
        if not helper.has_instance_data_scope_permission(request, config):
            raise AutoApiError(RESOURCE_ACCESS_DENIED)
        return config

    @action(methods=["get"], detail=False)
    @error_response("api")
    def retrieve(self, request: Request):
        """获取Mock 配置详情"""
        config = self._get_config(request)
        return ResponseData.success(RESPONSE_MSG_0001, ApiMockConfigSerializer(config).data)

    @action(methods=["get"], detail=False)
    @error_response("api")
    def assertion_methods(self, request: Request):
        """获取 Mock 可用断言方法"""
        return ResponseData.success(RESPONSE_MSG_0001, MockAssertionCatalog.catalog())

    @action(methods=["put"], detail=False)
    @error_response("api")
    def change_state(self, request: Request):
        """切换 Mock 配置启用状态"""
        config = self._get_config(request)
        allowed = {key: request.data[key] for key in ("enabled", "record_call_log") if key in request.data}
        if not allowed:
            return ResponseData.success(RESPONSE_MSG_0082, ApiMockConfigSerializer(config).data)
        serializer = ApiMockConfigSerializer(config, data=allowed, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        save_update_user(config, request, list(allowed))
        MockRuntimeCache.invalidate(config.mock_key)
        return ResponseData.success(RESPONSE_MSG_0082, ApiMockConfigSerializer(config).data)

    @action(methods=["post"], detail=False)
    @error_response("api")
    def debug(self, request: Request):
        """调试 Mock 配置并返回匹配结果"""
        config = self._get_config(request)
        return ResponseData.success(RESPONSE_MSG_0001, MockRuntimeService.debug(config, request.data))

    @action(methods=["get"], detail=False)
    @error_response("api")
    def logs(self, request: Request):
        """获取Mock 配置日志"""
        config = self._get_config(request)
        queryset = self._log_queryset(request, config)
        page_size = max(min(int(request.query_params.get("pageSize") or 20), 100), 1)
        page = max(int(request.query_params.get("page") or 1), 1)
        data, count = ApiMockConfigCRUD.paging_list(page_size, page, queryset, ApiMockRequestLogSerializer)
        return ResponseData.success(RESPONSE_MSG_0001, data, count)

    @staticmethod
    def _log_queryset(request: Request, config: ApiMockConfig):
        queryset = ApiMockRequestLog.objects.filter(mock_config=config).defer('callback_evidence')
        assertion_passed = request.query_params.get("assertion_passed")
        if assertion_passed not in (None, ""):
            queryset = queryset.filter(assertion_passed=str(assertion_passed).lower() in {"1", "true"})
        if request.query_params.get("response_status"):
            queryset = queryset.filter(response_status=request.query_params.get("response_status"))
        if request.query_params.get("trace_id"):
            queryset = queryset.filter(trace_id__contains=request.query_params.get("trace_id"))
        if request.query_params.get("request_path"):
            queryset = queryset.filter(request_path__contains=request.query_params.get("request_path"))
        return queryset.order_by("-create_time", "-id")

    @action(methods=["get"], detail=False)
    @error_response("api")
    def export_logs(self, request: Request):
        """导出 Mock 请求日志"""
        config = self._get_config(request)
        queryset = self._log_queryset(request, config)
        filename_time = self._local_datetime(timezone.now())
        filename = f"mock-{config.mock_key}-logs-{filename_time:%Y%m%d-%H%M%S}.csv"
        csv_file, content_length = self._build_log_csv_file(queryset)
        response = FileResponse(csv_file, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"
        response["Content-Length"] = str(content_length)
        response["X-Content-Type-Options"] = "nosniff"
        return response

    @classmethod
    def _build_log_csv_file(cls, queryset):
        csv_file = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
        try:
            for chunk in cls._stream_log_csv(queryset):
                csv_file.write(chunk.encode("utf-8"))
            content_length = csv_file.tell()
            csv_file.seek(0)
            return csv_file, content_length
        except Exception:
            csv_file.close()
            raise

    class _CsvEcho:
        @staticmethod
        def write(value):
            return value

    @classmethod
    def _stream_log_csv(cls, queryset):
        writer = csv.writer(cls._CsvEcho(), lineterminator="\n")
        yield "\ufeff"
        yield writer.writerow([
            "调用时间", "结果", "失败/异常原因", "请求方法", "响应状态码", "请求路径",
            "Trace ID", "命中规则", "耗时(ms)", "客户端IP", "Query参数", "请求头",
            "请求体", "断言结果", "响应头", "响应体", "响应Content-Type",
        ])
        for item in queryset.iterator(chunk_size=1000):
            yield writer.writerow(cls._log_csv_row(item))

    @classmethod
    def _log_csv_row(cls, item: ApiMockRequestLog) -> list:
        request_data = item.request_data if isinstance(item.request_data, dict) else {}
        response_data = item.response_data if isinstance(item.response_data, dict) else {}
        result = "异常" if item.error_message else "通过" if item.assertion_passed else "警告"
        reason = cls._log_result_reason(item)
        called_at = cls._local_datetime(item.create_time).strftime("%Y-%m-%d %H:%M:%S") if item.create_time else ""
        cells = [
            called_at,
            result,
            reason,
            MethodEnum.obj().get(item.method, "-"),
            item.response_status if item.response_status is not None else "",
            item.request_path,
            item.trace_id,
            item.rule_key or "",
            item.duration_ms,
            item.client_ip or "",
            cls._json_csv_value(request_data.get("query", {})),
            cls._json_csv_value(request_data.get("headers", {})),
            request_data.get("body", ""),
            cls._json_csv_value(item.assertion_results or []),
            cls._json_csv_value(response_data.get("headers", {})),
            response_data.get("body", ""),
            response_data.get("content_type", ""),
        ]
        return [cls._safe_csv_cell(value) for value in cells]

    @staticmethod
    def _json_csv_value(value) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)

    @staticmethod
    def _local_datetime(value):
        return timezone.localtime(value) if timezone.is_aware(value) else value

    @staticmethod
    def _safe_csv_cell(value):
        if not isinstance(value, str):
            return value
        return f"'{value}" if value.startswith(("=", "+", "-", "@")) else value

    @staticmethod
    def _log_result_reason(item: ApiMockRequestLog) -> str:
        if item.error_message:
            return f"平台异常：{item.error_message}"
        if item.assertion_passed:
            return ""
        failures = [
            result for result in (item.assertion_results or [])
            if isinstance(result, dict) and result.get("passed") is False
        ]
        if not failures:
            return "请求断言未通过，暂无失败明细"
        messages = []
        for failure in failures:
            name = failure.get("name") or failure.get("field") or failure.get("key") or "未命名断言"
            message = failure.get("message") or "请求值不符合预期"
            messages.append(f"{name}（{message}）")
        return f"请求断言未通过：{'；'.join(messages)}"

    @action(methods=["delete"], detail=False)
    @error_response("api")
    def clear_logs(self, request: Request):
        """清理指定 Mock 配置的请求日志"""
        config = self._get_config(request)
        deleted_count = MockRequestLogCleanupService.clear_config_logs(config.id)
        return ResponseData.success(RESPONSE_MSG_0005, {"deleted_count": deleted_count})

    @action(methods=["delete"], detail=False)
    @error_response("api")
    def clear_all_logs(self, request: Request):
        """清理全部 Mock 请求日志"""
        deleted_count = MockRequestLogCleanupService.clear_all_logs()
        return ResponseData.success(RESPONSE_MSG_0005, {"deleted_count": deleted_count})

    @action(methods=["get"], detail=False)
    @error_response("api")
    def log_detail(self, request: Request):
        """获取 Mock 请求日志详情"""
        item = ApiMockRequestLog.objects.select_related("mock_config").defer('callback_evidence').filter(
            id=request.query_params.get("id"),
        ).first()
        if item is None:
            return ResponseData.fail(RESPONSE_MSG_0158)
        helper = ApiMockConfigCRUD()
        if not helper.has_instance_data_scope_permission(request, item.mock_config):
            return ResponseData.fail(RESPONSE_MSG_0210)
        return ResponseData.success(RESPONSE_MSG_0001, ApiMockRequestLogSerializer(item).data)


class ApiMockRuntimeView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def get(self, request, *args, **kwargs):
        """处理 GET Mock 请求"""
        return self._execute(request, **kwargs)

    def post(self, request, *args, **kwargs):
        """处理 POST Mock 请求"""
        return self._execute(request, **kwargs)

    def put(self, request, *args, **kwargs):
        """处理 PUT Mock 请求"""
        return self._execute(request, **kwargs)

    def patch(self, request, *args, **kwargs):
        """处理 PATCH Mock 请求"""
        return self._execute(request, **kwargs)

    def delete(self, request, *args, **kwargs):
        """处理 DELETE Mock 请求"""
        return self._execute(request, **kwargs)

    def options(self, request, *args, **kwargs):
        """处理 OPTIONS Mock 请求"""
        return self._execute(request, **kwargs)

    @staticmethod
    def _error(status: int, code: str, message: str, trace_id: str):
        return JsonResponse(
            {"code": code, "message": message, "trace_id": trace_id},
            status=status,
            json_dumps_params={"ensure_ascii": False},
        )

    def _execute(self, request, mock_key: str, remaining_path: str = ""):
        started = time.monotonic()
        trace_id = f"mock_{uuid.uuid4().hex}"
        payload = None
        try:
            payload = MockRuntimeCache.load(mock_key)
            if payload is None:
                return self._error(404, "MOCK_NOT_FOUND", "Mock接口不存在", trace_id)
            if not payload.get("enabled"):
                return self._error(503, "MOCK_DISABLED", "Mock接口已停用", trace_id)
            result = MockRuntimeService.execute(payload, request, remaining_path or "/")
            response = HttpResponse(
                content=result.body.encode("utf-8"),
                status=result.status_code,
                content_type=result.content_type,
            )
            for key, value in result.headers.items():
                response[key] = value
            response["X-Mock-Trace-Id"] = result.trace_id
            response["Access-Control-Expose-Headers"] = ", ".join(
                sorted({"X-Mock-Trace-Id", *result.headers.keys()}, key=str.lower)
            )
            MockRuntimeService.record_response(
                payload, request, result, MockRuntimeService.elapsed_ms_since(started),
            )
            return response
        except MockRuntimeLookupError as error:
            response = self._error(error.status_code, error.code, error.message, error.trace_id)
            if payload is not None:
                MockRuntimeService.submit_error_log(
                    payload,
                    request,
                    remaining_path or "/",
                    error.trace_id,
                    error.status_code,
                    error.message,
                    MockRuntimeService.elapsed_ms_since(started),
                )
            return response
        except MockRequestDecryptionError as error:
            log.system.error(
                f"Mock请求解密配置读取失败：mock_key={mock_key}, trace_id={trace_id}"
            )
            return self._error(500, error.code, error.message, trace_id)
        except Exception as error:
            response = self._error(500, "MOCK_RUNTIME_ERROR", "Mock运行异常，请通过Trace ID排查", trace_id)
            if payload is not None:
                MockRuntimeService.submit_error_log(
                    payload,
                    request,
                    remaining_path or "/",
                    trace_id,
                    500,
                    str(error) or error.__class__.__name__,
                    MockRuntimeService.elapsed_ms_since(started),
                )
            log.system.error(
                f"Mock运行异常：mock_key={mock_key}, trace_id={trace_id}, error={error}"
            )
            return response
