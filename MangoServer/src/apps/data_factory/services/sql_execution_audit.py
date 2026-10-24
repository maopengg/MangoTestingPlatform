from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.apps.data_factory.exceptions import (
    DataFactoryError,
    SQL_AUDIT_REPLAY_FAILED,
    SQL_AUDIT_REQUEST_RUNNING,
    SQL_AUDIT_SOURCE_STAGE_REQUIRED,
    SQL_AUDIT_SOURCE_TYPE_REQUIRED,
)
from src.apps.data_factory.models import SqlExecutionRecord
from src.apps.system.services.system_config import SystemConfigService

SENSITIVE_KEY_PARTS = (
    'authorization', 'password', 'passwd', 'secret', 'token', 'api_key', 'apikey',
)
RESULT_PREVIEW_LIMIT = 1000


@dataclass
class SqlExecutionAuditHandle:
    record: SqlExecutionRecord
    started_monotonic: float
    existing: bool = False


class SqlExecutionAuditService:
    """统一 SQL 审计；调用方只传来源，不得自行复制执行记录。"""

    @staticmethod
    def _safe_scalar(value):
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, (datetime, Decimal)):
            return str(value)
        return str(value)

    @classmethod
    def sanitize(cls, value, key: str = ''):
        if any(part in key.lower() for part in SENSITIVE_KEY_PARTS):
            return '***'
        if isinstance(value, dict):
            return {str(k): cls.sanitize(v, str(k)) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls.sanitize(item) for item in value]
        return cls._safe_scalar(value)

    @staticmethod
    def operation_type(sql: str) -> str:
        match = re.match(r'^\s*([a-zA-Z]+)', sql or '')
        return (match.group(1).lower() if match else 'other')[:32]

    @staticmethod
    def fingerprint(sql: str) -> str:
        normalized = re.sub(r"'(?:''|[^'])*'", '?', sql or '')
        normalized = re.sub(r'\b\d+(?:\.\d+)?\b', '?', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip().lower()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    @classmethod
    def result_preview(cls, result: dict) -> tuple[str, bool]:
        payload = {
            'columns': result.get('columns') or [],
            'rows': result.get('rows') or [],
            'row_count': int(result.get('row_count') or 0),
            'affected_rows': int(result.get('affected_rows') or 0),
        }
        serialized = json.dumps(
            cls.sanitize(payload), ensure_ascii=False, separators=(',', ':'), default=str,
        )
        original_length = len(serialized)
        return serialized[:RESULT_PREVIEW_LIMIT], original_length > RESULT_PREVIEW_LIMIT

    @staticmethod
    def validate_source_context(source_context: dict | None) -> dict:
        context = dict(source_context or {})
        if not str(context.get('source_type') or '').strip():
            raise DataFactoryError(SQL_AUDIT_SOURCE_TYPE_REQUIRED)
        if not str(context.get('source_stage') or '').strip():
            raise DataFactoryError(SQL_AUDIT_SOURCE_STAGE_REQUIRED)
        return context

    @classmethod
    def start(
            cls, *, binding, project_product_id: int, test_env: int, sql: str,
            parameters: dict | None, source_context: dict, request_id: str | None,
            started_monotonic: float,
    ) -> SqlExecutionAuditHandle:
        context = cls.validate_source_context(source_context)
        request_id = str(request_id or uuid.uuid4().hex)[:64]
        existing = SqlExecutionRecord.objects.filter(request_id=request_id).first()
        if existing:
            return SqlExecutionAuditHandle(existing, started_monotonic, existing=True)
        threshold_ms = SystemConfigService.get_sql_slow_query_threshold_seconds() * 1000
        source_id = context.get('source_id')
        if source_id in (None, ''):
            source_id = context.get('case_id') or context.get('global_variable_id')
        record = SqlExecutionRecord.objects.create(
            request_id=request_id,
            source_type=str(context['source_type'])[:64],
            source_id=source_id or None,
            source_stage=str(context['source_stage'])[:64],
            source_detail=cls.sanitize(context),
            project_product_id=project_product_id,
            test_env=test_env,
            datasource_alias_id=binding.datasource_alias_id,
            database_id=getattr(binding, 'database_id', None),
            sql_text=sql,
            sql_parameters=cls.sanitize(parameters or {}),
            sql_fingerprint=cls.fingerprint(sql),
            status='running',
            slow_threshold_ms=threshold_ms,
        )
        return SqlExecutionAuditHandle(record, started_monotonic)

    @classmethod
    def replay_result(cls, handle: SqlExecutionAuditHandle) -> dict:
        record = handle.record
        if record.status == 'running':
            raise DataFactoryError(SQL_AUDIT_REQUEST_RUNNING, value=(record.request_id,))
        if record.status != 'success':
            raise DataFactoryError(
                SQL_AUDIT_REPLAY_FAILED,
                value=(record.error_message or record.request_id,),
            )
        payload = {}
        if record.result_preview and not record.result_truncated:
            try:
                payload = json.loads(record.result_preview)
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = {}
        return {
            'execution_type': 'query' if cls.operation_type(record.sql_text) in {'select', 'show', 'desc',
                                                                                 'describe'} else 'write',
            'columns': payload.get('columns') or [],
            'rows': payload.get('rows') or [],
            'result': payload.get('rows') or [],
            'row_count': record.row_count,
            'affected_rows': record.affected_rows,
            'truncated': record.result_truncated,
            'duration_ms': float(record.duration_ms or 0),
            'sql_execution_id': record.id,
            'is_slow': record.is_slow,
            'replayed': True,
        }

    @classmethod
    def finish_success(cls, handle: SqlExecutionAuditHandle, result: dict, duration_ms: float):
        preview, truncated = cls.result_preview(result)
        record = handle.record
        record.status = 'success'
        record.duration_ms = duration_ms
        record.row_count = int(result.get('row_count') or 0)
        record.affected_rows = int(result.get('affected_rows') or 0)
        record.result_preview = preview
        record.result_truncated = truncated
        record.is_slow = duration_ms > record.slow_threshold_ms
        record.save(update_fields=[
            'status', 'duration_ms', 'row_count', 'affected_rows',
            'result_preview', 'result_truncated', 'is_slow',
            'update_time',
        ])
        if record.is_slow:
            from src.apps.task_center.services.workbench.todo import WorkbenchTodoService
            WorkbenchTodoService.record_slow_sql(record)

    @classmethod
    def finish_failure(cls, handle: SqlExecutionAuditHandle, error: Exception, duration_ms: float):
        record = handle.record
        record.status = 'timeout' if isinstance(error, TimeoutError) else 'fail'
        record.duration_ms = duration_ms
        record.error_message = str(cls.sanitize(str(error)))[:2000]
        record.is_slow = duration_ms > record.slow_threshold_ms
        record.save(update_fields=[
            'status', 'duration_ms', 'error_message',
            'is_slow', 'update_time',
        ])
        if record.is_slow:
            from src.apps.task_center.services.workbench.todo import WorkbenchTodoService
            WorkbenchTodoService.record_slow_sql(record)
