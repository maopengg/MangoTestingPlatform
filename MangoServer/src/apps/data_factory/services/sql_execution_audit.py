from __future__ import annotations

import hashlib
import json
import re
import uuid
import shlex
import logging
import sqlparse
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from time import perf_counter
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, connections, transaction

from src.apps.data_factory.exceptions import (
    DataFactoryError,
    SQL_AUDIT_REPLAY_FAILED,
    SQL_AUDIT_REQUEST_RUNNING,
    SQL_AUDIT_SOURCE_STAGE_REQUIRED,
    SQL_AUDIT_SOURCE_TYPE_REQUIRED,
    DATASOURCE_AUDIT_UNAVAILABLE,
    DATASOURCE_AUDIT_COMPLETION_FAILED,
    DATASOURCE_AUDIT_REQUEST_CONFLICT,
    DATASOURCE_AUDIT_RESULT_UNAVAILABLE,
    DATASOURCE_ADMISSION_TIMEOUT,
    DATASOURCE_GOVERNOR_UNAVAILABLE,
    DATASOURCE_RECONCILIATION_REQUIRED,
    DATASOURCE_SETTLEMENT_FAILED,
    DATA_SOURCE_QUERY_RESULT_LIMIT_EXCEEDED,
)
from src.apps.data_factory.models import SqlExecutionRecord
from src.apps.data_factory.schemas.execution_audit import DatasourceAuditMetadata
from src.apps.data_factory.enums.audit import DatasourceAuditSourceEnum, DatasourceAuditStageEnum
from src.apps.data_factory.services.datasource_wait import DatasourceWaitService
from src.apps.data_factory.services.datasource_timing import DatasourceTimingService as Timing
from src.apps.system.services.system_config import SystemConfigService
from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventService
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.common.decorators.system_error import report_system_error
from src.common.enums.system_error import SystemErrorEventSource

log = logging.getLogger(__name__)

SENSITIVE_KEY_PARTS = (
    'authorization', 'password', 'passwd', 'pwd', 'secret', 'token', 'api_key', 'apikey',
    'cookie', 'credential', 'private_key', 'access_key',
)
RESULT_PREVIEW_LIMIT = 1000
_active_audit = ContextVar('datasource_active_audit', default=None)
_source_context = ContextVar('datasource_audit_source', default=None)


@dataclass
class SqlExecutionAuditHandle:
    record: SqlExecutionRecord
    started_monotonic: float
    existing: bool = False
    statement_claimed: bool = False
    children: list = field(default_factory=list)
    wait_started: float = field(default_factory=DatasourceWaitService.elapsed)
    admission_wait_ms: float = 0.0
    timing_started: dict = field(default_factory=Timing.snapshot)


class SqlExecutionAuditService:
    """统一数据源审计；调用方只传来源，不得自行复制执行记录。"""

    @staticmethod
    def report_audit_failure(error, stage):
        from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService
        DatasourceInfrastructureService.capture(DataFactoryError(
            DATASOURCE_AUDIT_COMPLETION_FAILED if stage == 'completion' else DATASOURCE_AUDIT_UNAVAILABLE))
        # 上报底层故障，而非后续对外包装的业务异常；不携带操作内容或凭证。
        try:
            service_name = settings.MANGO_SERVICE_NAME
            source = next((source for source, service in SystemErrorEventService.SOURCE_SERVICE_MAP.items()
                           if service == service_name), SystemErrorEventSource.HTTP)
            report_system_error(error, source=source, service_name=service_name,
                                request_path=f'datasource_audit:{stage}')
        except Exception:
            # 系统异常表也可能不可用，不能覆盖原审计错误，更不能因此继续执行。
            log.exception('数据源审计故障的系统异常记录失败')

    @staticmethod
    @contextmanager
    def scope(handle):
        token = _active_audit.set(handle)
        try:
            yield handle
        finally:
            _active_audit.reset(token)

    @staticmethod
    def active():
        return _active_audit.get()

    @staticmethod
    def current_source():
        return dict(_source_context.get() or {})

    @staticmethod
    @contextmanager
    def source(context):
        token = _source_context.set({**(_source_context.get() or {}), **context})
        try:
            yield
        finally:
            _source_context.reset(token)

    @staticmethod
    def database_alias():
        # 独立连接确保 Case 外层平台事务回滚时审计仍存在；正常自动提交复用 default。
        if not connections['default'].in_atomic_block:
            return 'default'
        alias = 'datasource_audit'
        if alias not in connections.databases:
            connections.databases[alias] = dict(connections['default'].settings_dict)
        return alias

    @classmethod
    def call(cls, database, operation, callback, *, stage=DatasourceAuditStageEnum.QUERY.value,
             source_type=DatasourceAuditSourceEnum.CONNECTION.value, result_summary=None):
        from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService
        with cls.source({'source_stage': stage, **cls.current_source()}):
            with DatasourceGovernorService.operation(database) as admission:
                with cls.source({**cls.current_source(), **({'performance': admission} if admission else {})}):
                    return cls._call_admitted(database, operation, callback, stage=stage, source_type=source_type,
                                              result_summary=result_summary)

    @classmethod
    def _call_admitted(cls, database, operation, callback, *, stage, source_type, result_summary):
        active = cls.active()
        if active is not None and (
                getattr(active.record, 'database_id', None) == getattr(database, 'id', None)
                and getattr(active.record, 'datasource_type', None) == getattr(database, 'db_type', None)):
            return callback()
        started = perf_counter()
        handle = cls.start(
            database=database, sql=operation, parameters=None, request_id=None,
            source_context={
                'source_type': source_type, 'source_id': getattr(database, 'id', None),
                'source_stage': stage, **(_source_context.get() or {}),
            }, started_monotonic=started,
        )
        started = perf_counter()
        try:
            with cls.scope(handle):
                result = callback()
        except Exception as error:
            cls.finish_failure(handle, error, round((perf_counter() - started) * 1000, 2))
            raise
        duration = round((perf_counter() - started) * 1000, 2)
        if isinstance(result, dict) and (result.get('connected') is False or result.get('status') == 'failed'):
            cls.finish_failure(handle, OSError(), duration)
        else:
            summary = result_summary(result) if result_summary is not None else result
            cls.finish_success(handle, summary if isinstance(summary, dict) else {'result': summary}, duration)
        return result

    @staticmethod
    def audited(stage):
        """独立连接协议入口使用；已有业务审计作用域时只执行、不重复记录。"""
        def decorate(method):
            @wraps(method)
            def wrapped(cls, database, *args, **kwargs):
                if stage == DatasourceAuditStageEnum.TEST_CONNECTION.value:
                    from src.apps.data_factory.schemas.datasource_target import DatasourceTarget
                    from src.apps.data_factory.services.datasource_target import DatasourceTargetService
                    if not isinstance(database, DatasourceTarget):
                        database = DatasourceTargetService.maintenance(database)
                operation = stage
                if stage == DatasourceAuditStageEnum.REDIS_COMMAND.value:
                    operation = args[0] if args else kwargs.get('command', stage)
                elif stage == DatasourceAuditStageEnum.ES_SEARCH.value:
                    operation = {'operation': 'search', 'index': args[0] if args else kwargs.get('index'),
                                 'query': args[1] if len(args) > 1 else kwargs.get('query')}
                return SqlExecutionAuditService.call(
                    database, operation, lambda: method(cls, database, *args, **kwargs), stage=stage,
                )
            return wrapped
        return decorate

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
        if isinstance(value, str) and value.lstrip().startswith(('{', '[')):
            try:
                return cls.sanitize(json.loads(value))
            except (ValueError, RecursionError):
                return '[无法安全解析的结构化内容已隐藏]'
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
        # SQL 的二维 rows 要按 columns 识别敏感列，不能只遍历字典键。
        payload = dict(result)
        columns = result.get('columns') or []
        if columns and result.get('rows'):
            payload['rows'] = [
                [cls.sanitize(value, str(columns[index]) if index < len(columns) else '')
                 for index, value in enumerate(row)] if isinstance(row, (list, tuple)) else cls.sanitize(row)
                for row in result['rows']
            ]
            if 'result' in payload:
                payload['result'] = payload['rows']
        serialized = json.dumps(
            cls.sanitize(payload), ensure_ascii=False, separators=(',', ':'), default=str,
        )
        original_length = len(serialized)
        return serialized[:RESULT_PREVIEW_LIMIT], original_length > RESULT_PREVIEW_LIMIT

    @classmethod
    def safe_content(cls, content, datasource_type):
        if isinstance(content, dict):
            return json.dumps(cls.sanitize(content), ensure_ascii=False, separators=(',', ':'), default=str)
        value = str(content or '')
        if datasource_type == DataSourceTypeEnum.REDIS.value:
            try:
                parts = shlex.split(value)
            except ValueError:
                return '[无法安全解析的命令已隐藏]'
            # key/value 都可能含密钥；记录命令类型和参数个数，不保存自由文本值。
            return ' '.join([parts[0].upper(), *['?' for _ in parts[1:]]]) if parts else ''
        # 自由 SQL 字面量和注释不能按业务字段可靠判断，统一隐藏；资产定位使用来源 ID。
        value = sqlparse.format(value, strip_comments=True)
        value = re.sub(r'(\$[A-Za-z_]\w*\$|\$\$).*?\1', '?', value, flags=re.DOTALL)
        value = re.sub(r'\b0x[0-9a-f]+\b', '?', value, flags=re.IGNORECASE)
        value = re.sub(r"'(?:''|[^'\\]|\\.)*'", "'?'", value)
        if datasource_type != DataSourceTypeEnum.POSTGRESQL.value:
            value = re.sub(r'"(?:""|[^"\\]|\\.)*"', '"?"', value)
        return re.sub(r'\b\d+(?:\.\d+)?\b', '?', value)

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
            cls, *, binding=None, project_product_id: int | None = None, test_env: int | None = None, sql,
            parameters: dict | None, source_context: dict, request_id: str | None,
            started_monotonic: float, database=None,
    ) -> SqlExecutionAuditHandle:
        context = cls.validate_source_context({**(_source_context.get() or {}), **source_context})
        context.pop('slow_notice_recorded', None)
        database = database or (binding.database if binding is not None else None)
        datasource_type = database.db_type
        if binding is None:
            project_product_id = getattr(database, 'project_product_id', None)
            test_env = getattr(database, 'test_env', None)
        alias_id = (binding.datasource_alias_id if binding is not None
                    else getattr(database, 'datasource_alias_id', None))
        database_id = getattr(binding, 'database_id', None) if binding is not None else getattr(database, 'id', None)
        metadata = DatasourceAuditMetadata(
            target_kind='logical_database' if alias_id is not None else 'connection',
            database_name=getattr(database, 'database_name', '') or '',
            redis_db=getattr(database, 'redis_db', None),
            index=sql.get('index') if isinstance(sql, dict) else None,
            operation=str(sql.get('operation') or 'search') if isinstance(sql, dict) else cls.operation_type(str(sql)),
        )
        context.update(metadata.model_dump(exclude_unset=True))
        if datasource_type == DataSourceTypeEnum.REDIS.value:
            context['sensitive_result'] = any(key in str(sql).lower() for key in SENSITIVE_KEY_PARTS)
        # 原始操作仅用于带密钥 HMAC，避免同 ID 不同操作被误判为重试；不落原始值。
        import hmac
        signature = hmac.new(str(settings.SECRET_KEY).encode(), json.dumps(
            [datasource_type, database_id, project_product_id, test_env,
             alias_id, context, sql, parameters],
            sort_keys=True, default=str, ensure_ascii=False,
        ).encode(), hashlib.sha256).hexdigest()
        context['request_signature'] = signature
        request_id = str(request_id or uuid.uuid4().hex)
        if len(request_id) > 64:
            raise DataFactoryError(DATASOURCE_AUDIT_REQUEST_CONFLICT)
        threshold_ms = SystemConfigService.get_sql_slow_query_threshold_seconds() * 1000
        source_id = context.get('source_id')
        if source_id in (None, ''):
            source_id = context.get('case_id') or context.get('global_variable_id')
        values = dict(
            request_id=request_id,
            source_type=str(context['source_type'])[:64],
            source_id=source_id or None,
            source_stage=str(context['source_stage'])[:64],
            source_detail=cls.sanitize(context),
            project_product_id=project_product_id,
            test_env=test_env,
            datasource_alias_id=alias_id,
            database_id=database_id,
            datasource_type=datasource_type,
            sql_text=cls.safe_content(sql, datasource_type),
            sql_parameters=cls.sanitize_parameters(parameters or {}),
            sql_fingerprint=cls.fingerprint(f'{DataSourceTypeEnum.obj().get(datasource_type, datasource_type)}:{cls.safe_content(sql, datasource_type)}'),
            status='running',
            slow_threshold_ms=threshold_ms,
        )
        from src.apps.system.services.runtime_center.process_identity import RuntimeProcessIdentity
        # 本机生成的进程UUID不是授权token；单独存储，不能被通用凭据脱敏抹掉。
        values['source_detail']['execution_owner'] = RuntimeProcessIdentity.current()
        using = cls.database_alias()
        try:
            try:
                with transaction.atomic(using=using):
                    record = SqlExecutionRecord.objects.using(using).create(**values)
            except IntegrityError:
                record = SqlExecutionRecord.objects.using(using).get(request_id=request_id)
                if record.source_detail.get('request_signature') != signature:
                    raise DataFactoryError(DATASOURCE_AUDIT_REQUEST_CONFLICT)
                return SqlExecutionAuditHandle(record, started_monotonic, existing=True)
        except DataFactoryError:
            raise
        except Exception as error:
            log.exception('数据源执行审计创建失败，已阻止执行')
            cls.report_audit_failure(error, 'create')
            from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService
            raise DatasourceInfrastructureService.annotate(DataFactoryError(DATASOURCE_AUDIT_UNAVAILABLE),
                                                          request_id=request_id) from error
        return SqlExecutionAuditHandle(record, perf_counter())

    @classmethod
    def sanitize_parameters(cls, parameters):
        if not isinstance(parameters, dict):
            return {'bindings': '[位置参数已隐藏]'}
        return {key: '[位置参数已隐藏]' if key == 'bindings' else cls.sanitize(value, key)
                for key, value in parameters.items()}

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
        # 不把脱敏/截断摘要当作真实查询结果，也不再次访问数据源。
        from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService
        raise DatasourceInfrastructureService.annotate(DataFactoryError(DATASOURCE_AUDIT_RESULT_UNAVAILABLE),
                                                      request_id=record.request_id)

    @classmethod
    def measured_duration(cls, handle, duration_ms):
        waited_ms = max(0, (DatasourceWaitService.elapsed() - handle.wait_started) * 1000)
        handle.record.source_detail = {**(handle.record.source_detail or {}),
                                       'resource_wait_ms': round(waited_ms + handle.admission_wait_ms, 2),
                                       'timing_ms': Timing.delta(handle.timing_started)}
        return round(max(0, duration_ms - waited_ms), 2)

    @classmethod
    def finish_success(cls, handle: SqlExecutionAuditHandle, result: dict, duration_ms: float):
        duration_ms = cls.measured_duration(handle, duration_ms)
        record = handle.record
        payload = result
        if (record.source_detail or {}).get('sensitive_result'):
            payload = {'result': '***'}
        preview, truncated = cls.result_preview(payload)
        record.status = 'success'
        record.duration_ms = duration_ms
        record.row_count = int(result.get('row_count') or 0)
        record.affected_rows = int(result.get('affected_rows') or 0)
        record.result_preview = preview
        record.result_truncated = truncated
        record.is_slow = duration_ms > record.slow_threshold_ms
        cls.save_completion(record, update_fields=[
            'status', 'duration_ms', 'row_count', 'affected_rows',
            'result_preview', 'result_truncated', 'is_slow',
            'source_detail', 'update_time',
        ])
        cls.notify_slow(record)

    @classmethod
    def finish_failure(cls, handle: SqlExecutionAuditHandle, error: Exception, duration_ms: float):
        from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService
        error._datasource_audit_request_id = handle.record.request_id
        if isinstance(error, DataFactoryError):
            DatasourceInfrastructureService.annotate(error, request_id=handle.record.request_id,
                                                  database_id=getattr(handle.record, 'database_id', None))
        with cls.scope(handle):
            DatasourceInfrastructureService.capture(error, result_unknown=True)
        duration_ms = cls.measured_duration(handle, duration_ms)
        record = handle.record
        record.status = 'timeout' if cls.is_timeout(error) else 'fail'
        record.duration_ms = duration_ms
        record.error_message = '数据源操作超时，结果需核查' if record.status == 'timeout' else '数据源操作失败，请结合来源及系统错误日志排查'
        error_code = getattr(error, 'code', None)
        not_sent = getattr(error, '_datasource_not_sent', False) and not handle.statement_claimed
        for definition in (DATASOURCE_ADMISSION_TIMEOUT, DATASOURCE_GOVERNOR_UNAVAILABLE,
                           DATASOURCE_RECONCILIATION_REQUIRED, DATASOURCE_SETTLEMENT_FAILED):
            if error_code == definition.code and (not_sent or definition == DATASOURCE_SETTLEMENT_FAILED):
                # 这些是固定、安全的准入提示；不能把未知业务异常原文写入审计。
                record.error_message = error.msg
                break
        row_limit_error = isinstance(error, DataFactoryError) and error_code == DATA_SOURCE_QUERY_RESULT_LIMIT_EXCEEDED.code
        if isinstance(error, DataFactoryError) and 34173 <= error_code <= 34194:
            record.error_message = error.msg
        if isinstance(error_code, int):
            record.error_message = f'[{error_code}] {record.error_message}'
        from src.apps.data_factory.services.data_source_error import DataSourceErrorService
        if not_sent or DataSourceErrorService.confirmed_rejection(error):
            outcome_unknown = False
        elif row_limit_error:
            outcome_unknown = bool(getattr(error, '_datasource_outcome_unknown', False))
        else:
            outcome_unknown = True
        record.source_detail = {**record.source_detail, 'outcome_unknown': outcome_unknown,
                                'error_category': type(error).__name__,
                                'error_code': error_code if isinstance(error_code, int) else None}
        record.is_slow = duration_ms > record.slow_threshold_ms
        cls.save_completion(record, update_fields=[
            'status', 'duration_ms', 'error_message',
            'source_detail', 'is_slow', 'update_time',
        ])
        cls.notify_slow(record)

    @staticmethod
    def is_timeout(error):
        seen = set()
        while error is not None and id(error) not in seen:
            seen.add(id(error))
            if isinstance(error, TimeoutError) or 'timeout' in type(error).__name__.lower():
                return True
            reason = getattr(error, 'reason', None)
            error = getattr(error, 'orig', None) or error.__cause__ or (reason if isinstance(reason, BaseException) else None)
        return False

    @staticmethod
    def save_completion(record, *, update_fields):
        try:
            record.save(update_fields=update_fields)
        except Exception as error:
            log.exception(f'数据源执行审计终态保存失败，record_id={record.id}，禁止自动重放')
            SqlExecutionAuditService.report_audit_failure(error, 'completion')
            from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService
            raise DatasourceInfrastructureService.annotate(DataFactoryError(DATASOURCE_AUDIT_COMPLETION_FAILED),
                                                          request_id=getattr(record, 'request_id', None),
                                                          database_id=getattr(record, 'database_id', None)) from error

    @staticmethod
    def notify_slow(record):
        if not record.is_slow:
            return
        try:
            from src.apps.task_center.services.workbench.todo import WorkbenchTodoService
            WorkbenchTodoService.record_slow_sql(record)
            def acknowledge():
                try:
                    record.source_detail = {**record.source_detail, 'slow_notice_recorded': True}
                    record.save(update_fields=['source_detail'])
                except Exception:
                    log.exception(f'慢执行通知确认失败，record_id={record.id}')
            # 若待办属于外层平台事务，必须等提交后才确认，否则回滚会丢待办。
            transaction.on_commit(acknowledge, using='default')
        except Exception:
            log.exception(f'慢数据源操作待办生成失败，record_id={record.id}')

    @classmethod
    def recover_stale(cls, *, batch_size=200):
        from datetime import timedelta
        from django.utils import timezone
        # 只标识长时间未回写的结果不确定记录；绝不根据超时自动重执行。
        from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
        now = timezone.now()
        cutoff = now - timedelta(days=1)
        recovered = 0
        for record in SqlExecutionRecord.objects.filter(status='running', update_time__lt=now-timedelta(minutes=1)).order_by('id')[:batch_size]:
            owner = (record.source_detail or {}).get('execution_owner')
            drained = ServiceHeartbeatService.completed_mcp_process(owner, getattr(record, 'create_time', record.update_time))
            if not drained and record.update_time >= cutoff:
                continue
            detail = {**record.source_detail, 'outcome_unknown': True,
                      'execution_owner_completed': drained}
            recovered += SqlExecutionRecord.objects.filter(id=record.id, status='running', update_time=record.update_time).update(
                status='fail', source_detail=detail, update_time=timezone.now(),
                error_message='执行进程未回写终态，实际结果不确定，请核查，禁止自动重放',
            )
        return {'recovered_audit_count': recovered,
                'reconciled_slow_audit_count': cls.reconcile_slow(batch_size=batch_size)}

    @classmethod
    def reconcile_slow(cls, *, batch_size=200):
        from django.db.models import Q
        records = SqlExecutionRecord.objects.filter(is_slow=True).filter(
            Q(source_detail__slow_notice_recorded__isnull=True) | Q(source_detail__slow_notice_recorded=False),
        ).exclude(status='running').order_by('id')[:batch_size]
        count = 0
        for record in records:
            cls.notify_slow(record)
            count += 1
        return count
