from __future__ import annotations

import hashlib
import html
import json
import random
from contextlib import contextmanager
from datetime import timedelta

import time
from django.db import OperationalError, connection
from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from mangotools.enums import StatusEnum

from src.apps.auto_api.enums import (
    ApiAuthRefreshModeEnum,
    ApiAuthRefreshStatusEnum,
    ApiCaseReleaseStatusEnum,
)
from src.apps.auto_api.models import ApiAuthConfig, ApiCaseRelease
from src.apps.auto_ui.enums import UiAuthRefreshModeEnum, UiAuthRefreshStatusEnum
from src.apps.auto_ui.models import UiAuthConfig
from src.apps.data_factory.enums import DataFactoryCleanupStatusEnum
from src.apps.data_factory.models import (
    DataFactoryEntity,
    DataFactoryExecution,
    DataFactoryExecutionItem,
)
from src.apps.system.enums import CacheDataKeyEnum
from src.apps.system.services.system_config import SystemConfigService
from src.apps.task_center.enums import (
    WorkbenchTodoEventTypeEnum,
    WorkbenchTodoSeverityEnum,
    WorkbenchTodoSourceTypeEnum,
    WorkbenchTodoStatusEnum,
)
from src.apps.task_center.models import WorkbenchTodo
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.apps.test_center.services.test_suite.base_notice import NoticeMain
from src.apps.user.services.credential import UserCredentialService
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.common.logging import log


class WorkbenchTodoService:
    DEFAULT_MANUAL_NOTICE_MINUTES = 24 * 60
    RECONCILE_LOCK_NAME = 'mango_workbench_todo_reconcile'
    DEADLOCK_MAX_ATTEMPTS = 3
    DEADLOCK_BASE_DELAY_SECONDS = 0.02
    API_CASE_PREPUBLICATION_PREVIEW_LIMIT = 50
    MANUAL_HANDLING_EVENT_TYPES = {
        WorkbenchTodoEventTypeEnum.DATA_FACTORY_SCHEMA_REVIEW.value,
        WorkbenchTodoEventTypeEnum.DATA_FACTORY_CLEANUP_FAILED.value,
        WorkbenchTodoEventTypeEnum.SLOW_SQL.value,
    }

    @classmethod
    def record_slow_sql(cls, record):
        """按来源和操作指纹聚合；无产品连接记录保留运维告警，不伪造产品待办。"""
        if record.project_product_id is None:
            log.system.warning(f'全局连接慢执行，请在数据源执行记录排查：record_id={record.id}')
            return None
        occurred_at = record.update_time or timezone.now()
        source_detail = dict(record.source_detail or {})
        target_key = hashlib.sha256(json.dumps([
            record.datasource_type, record.database_id, source_detail.get('database_name'),
            source_detail.get('redis_db'), source_detail.get('index'),
        ], default=str, ensure_ascii=False).encode()).hexdigest()[:20]
        event_key = (
            f'slow-sql:{record.project_product_id}:{record.test_env}:'
            f'{record.datasource_alias_id}:{record.source_type}:{record.source_id or 0}:'
            f'{record.source_stage}:{record.sql_fingerprint}:{target_key}'
        )
        event_key = 'slow-datasource:' + hashlib.sha256(event_key.encode()).hexdigest()
        existing = WorkbenchTodo.objects.filter(event_key=event_key).only('details').first()
        previous = dict(existing.details or {}) if existing else {}
        occurrence_count = int(previous.get('occurrence_count') or 0) + (previous.get('sql_execution_id') != record.id)
        duration_ms = float(record.duration_ms or 0)
        max_duration_ms = max(float(previous.get('max_duration_ms') or 0), duration_ms)
        operation_name = {
            DataSourceTypeEnum.REDIS.value: 'Redis操作',
            DataSourceTypeEnum.ELASTICSEARCH.value: 'ES操作',
        }.get(record.datasource_type, 'SQL')
        return cls._upsert(event_key, {
            'source_type': WorkbenchTodoSourceTypeEnum.SQL_EXECUTION.value,
            'event_type': WorkbenchTodoEventTypeEnum.SLOW_SQL.value,
            'source_id': record.id,
            'project_product_id': record.project_product_id,
            'module_id': source_detail.get('module_id'),
            'severity': WorkbenchTodoSeverityEnum.WARNING.value,
            'title': f'慢{operation_name}：{record.source_type} / {record.source_stage}',
            'summary': (
                f'{operation_name}执行耗时 {duration_ms / 1000:.3f} 秒，超过阈值 '
                f'{record.slow_threshold_ms / 1000:.0f} 秒。'
            ),
            'due_at': occurred_at,
            'occurred_at': occurred_at,
            'details': {
                **previous,
                'source_name': '数据源执行记录',
                'datasource_type': record.datasource_type,
                'database_id': record.database_id,
                'sql_execution_id': record.id,
                'source_type': record.source_type,
                'source_id': record.source_id,
                'source_stage': record.source_stage,
                'source_detail': source_detail,
                'test_env': record.test_env,
                'datasource_alias_id': record.datasource_alias_id,
                'sql_fingerprint': record.sql_fingerprint,
                'sql_text': record.sql_text,
                'duration_ms': duration_ms,
                'max_duration_ms': max_duration_ms,
                'threshold_ms': record.slow_threshold_ms,
                'occurrence_count': occurrence_count,
                'first_occurred_at': previous.get('first_occurred_at') or occurred_at.isoformat(),
                'last_occurred_at': occurred_at.isoformat(),
            },
        })

    @staticmethod
    def _timestamp_key(value) -> str:
        return value.strftime('%Y%m%d%H%M%S') if value else 'unknown'

    @staticmethod
    def _format_datetime(value) -> str:
        display_value = timezone.localtime(value) if timezone.is_aware(value) else value
        return display_value.strftime('%Y-%m-%d %H:%M')

    @staticmethod
    def _schema_difference_fingerprint(differences: list) -> str:
        payload = json.dumps(differences, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    @classmethod
    def _upsert(
            cls,
            event_key: str,
            defaults: dict,
            *,
            notify_owner: bool = True,
    ) -> WorkbenchTodo:
        todo, created = WorkbenchTodo.objects.get_or_create(
            event_key=event_key,
            defaults={
                **defaults,
                'status': WorkbenchTodoStatusEnum.PENDING.value,
            },
        )
        if created and notify_owner:
            cls._notify_owner(todo)
        if created:
            return todo
        was_pending = todo.status == WorkbenchTodoStatusEnum.PENDING.value
        if todo.status == WorkbenchTodoStatusEnum.HANDLED.value and todo.handled_by_id is not None:
            existing_fingerprint = (todo.details or {}).get('difference_fingerprint')
            incoming_fingerprint = (defaults.get('details') or {}).get('difference_fingerprint')
            if not incoming_fingerprint or existing_fingerprint == incoming_fingerprint:
                return todo
        for field, value in defaults.items():
            setattr(todo, field, value)
        todo.status = WorkbenchTodoStatusEnum.PENDING.value
        todo.handled_by = None
        todo.handled_at = None
        todo.handle_note = None
        todo.save(update_fields=[
            *defaults.keys(),
            'status',
            'handled_by',
            'handled_at',
            'handle_note',
            'update_time',
        ])
        if not was_pending and notify_owner:
            cls._notify_owner(todo)
        return todo

    @classmethod
    def can_mark_handled(cls, todo: WorkbenchTodo) -> bool:
        return (
                todo.status == WorkbenchTodoStatusEnum.PENDING.value
                and todo.event_type in cls.MANUAL_HANDLING_EVENT_TYPES
        )

    @classmethod
    def mark_handled(cls, todo: WorkbenchTodo, user, note: str = '') -> bool:
        if not cls.can_mark_handled(todo) or user is None:
            return False
        handled_at = timezone.now()
        details = dict(todo.details or {})
        if (
                todo.event_type == WorkbenchTodoEventTypeEnum.DATA_FACTORY_SCHEMA_REVIEW.value
                and not details.get('difference_fingerprint')
        ):
            details['difference_fingerprint'] = cls._schema_difference_fingerprint(
                details.get('differences') or []
            )
        updated = WorkbenchTodo.objects.filter(
            id=todo.id,
            status=WorkbenchTodoStatusEnum.PENDING.value,
            event_type__in=cls.MANUAL_HANDLING_EVENT_TYPES,
        ).update(
            status=WorkbenchTodoStatusEnum.HANDLED.value,
            handled_by=user,
            handled_at=handled_at,
            handle_note=note[:500] or '用户确认已处理。',
            details=details,
            update_time=handled_at,
        )
        if not updated:
            return False
        todo.status = WorkbenchTodoStatusEnum.HANDLED.value
        todo.handled_by = user
        todo.handled_at = handled_at
        todo.handle_note = note[:500] or '用户确认已处理。'
        todo.details = details
        return True

    @staticmethod
    def _is_mysql_deadlock(error: OperationalError) -> bool:
        return bool(error.args) and error.args[0] == 1213

    @classmethod
    def _resolve_queryset(cls, queryset, note: str) -> int:
        for attempt in range(cls.DEADLOCK_MAX_ATTEMPTS):
            resolved_at = timezone.now()
            try:
                return queryset.filter(status=WorkbenchTodoStatusEnum.PENDING.value).update(
                    status=WorkbenchTodoStatusEnum.HANDLED.value,
                    handled_by=None,
                    handled_at=resolved_at,
                    handle_note=note,
                    update_time=resolved_at,
                )
            except OperationalError as error:
                if (
                        not cls._is_mysql_deadlock(error)
                        or attempt + 1 >= cls.DEADLOCK_MAX_ATTEMPTS
                ):
                    raise
                delay = (
                        cls.DEADLOCK_BASE_DELAY_SECONDS * (2 ** attempt)
                        + random.uniform(0, cls.DEADLOCK_BASE_DELAY_SECONDS)
                )
                log.system.warning(
                    '首页风险待办自动关闭遇到数据库死锁，准备重试：'
                    f'attempt={attempt + 1}, delay={delay:.3f}s'
                )
                time.sleep(delay)
        return 0

    @classmethod
    @contextmanager
    def _reconcile_lock(cls):
        """同一数据库只允许一个进程执行全量待办对账。"""
        if connection.vendor != 'mysql':
            yield True
            return

        with connection.cursor() as cursor:
            cursor.execute('SELECT GET_LOCK(%s, 0)', [cls.RECONCILE_LOCK_NAME])
            acquired = cursor.fetchone()[0] == 1
        try:
            yield acquired
        finally:
            if acquired:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT RELEASE_LOCK(%s)', [cls.RECONCILE_LOCK_NAME])

    @classmethod
    def _auth_details(cls, config, source_name: str, effective_expires_at=None) -> dict:
        expires_at = effective_expires_at or config.expires_at
        return {
            'source_name': source_name,
            'auth_name': config.name,
            'test_env': config.test_env,
            'test_env_name': EnvironmentEnum.get_value(config.test_env) if config.test_env is not None else '-',
            'refresh_mode': config.refresh_mode,
            'expires_at': expires_at.isoformat() if expires_at else None,
            'last_refresh_time': (
                config.last_refresh_time.isoformat() if config.last_refresh_time else None
            ),
            'last_refresh_error': config.last_refresh_error or '',
        }

    @classmethod
    def _record_auth_failure(cls, config, source_type: int, source_name: str):
        occurred_at = config.last_refresh_time or config.update_time or timezone.now()
        event_key = (
            f'auth:{source_type}:{config.id}:refresh-failed:{cls._timestamp_key(occurred_at)}'
        )
        return cls._upsert(event_key, {
            'source_type': source_type,
            'event_type': WorkbenchTodoEventTypeEnum.AUTH_REFRESH_FAILED.value,
            'source_id': config.id,
            'project_product_id': config.project_product_id,
            'module_id': None,
            'severity': WorkbenchTodoSeverityEnum.DANGER.value,
            'title': f'{source_name}刷新失败：{config.name}',
            'summary': config.last_refresh_error or '最近一次授权刷新失败，请检查授权配置。',
            'due_at': occurred_at,
            'occurred_at': occurred_at,
            'details': cls._auth_details(config, source_name),
        })

    @classmethod
    def record_ui_auth_refresh_failure(cls, config_id: int):
        config = UiAuthConfig.objects.select_related('project_product').filter(id=config_id).first()
        if not config or config.last_refresh_status != UiAuthRefreshStatusEnum.FAIL.value:
            return None
        return cls._record_auth_failure(
            config,
            WorkbenchTodoSourceTypeEnum.UI_AUTH.value,
            '前端授权',
        )

    @classmethod
    def record_api_auth_refresh_failure(cls, config_id: int):
        config = ApiAuthConfig.objects.select_related('project_product').filter(id=config_id).first()
        if not config or config.last_refresh_status != ApiAuthRefreshStatusEnum.FAIL.value:
            return None
        return cls._record_auth_failure(
            config,
            WorkbenchTodoSourceTypeEnum.API_AUTH.value,
            '服务授权',
        )

    @classmethod
    def _record_auth_expiry(cls, config, source_type: int, source_name: str, manual_mode: int):
        if (
                source_type == WorkbenchTodoSourceTypeEnum.API_AUTH.value
                and config.refresh_mode == manual_mode
        ):
            return None
        expires_at = config.expires_at
        if (
                not expires_at
                and config.refresh_mode == manual_mode
                and config.last_refresh_time
                and int(getattr(config, 'token_ttl', 0) or 0) > 0
        ):
            expires_at = config.last_refresh_time + timedelta(minutes=int(config.token_ttl))
        if not expires_at:
            return None
        notice_minutes = int(config.expire_notice_minutes or 0)
        if config.refresh_mode == manual_mode:
            notice_minutes = max(notice_minutes, cls.DEFAULT_MANUAL_NOTICE_MINUTES)
        now = timezone.now()
        notify_at = expires_at - timedelta(minutes=notice_minutes)
        if now < notify_at:
            return None
        expired = now >= expires_at
        event_type = (
            WorkbenchTodoEventTypeEnum.AUTH_EXPIRED.value
            if expired
            else WorkbenchTodoEventTypeEnum.AUTH_EXPIRING.value
        )
        remaining_seconds = int((expires_at - now).total_seconds())
        summary = (
            f'授权已于 {cls._format_datetime(expires_at)} 过期，请手动更新。'
            if expired
            else f'授权将在 {max(remaining_seconds // 60, 0)} 分钟后到期，请提前更新。'
        )
        event_key = (
            f'auth:{source_type}:{config.id}:expiry:{cls._timestamp_key(expires_at)}'
        )
        title = f'{source_name}{"已过期" if expired else "即将到期"}：{config.name}'
        defaults = {
            'source_type': source_type,
            'event_type': event_type,
            'source_id': config.id,
            'project_product_id': config.project_product_id,
            'module_id': None,
            'severity': (
                WorkbenchTodoSeverityEnum.DANGER.value
                if expired
                else WorkbenchTodoSeverityEnum.WARNING.value
            ),
            'title': title,
            'summary': summary,
            'due_at': expires_at,
            'occurred_at': notify_at,
            'details': cls._auth_details(config, source_name, expires_at),
        }
        todo = cls._upsert(event_key, defaults)
        cls._notify_auth_notice_group(config, source_type, title, summary)
        return todo

    @classmethod
    def _notify_auth_notice_group(
            cls,
            config,
            source_type: int,
            title: str,
            summary: str,
    ) -> bool:
        notice_group_id = getattr(config, 'notice_group_id', None)
        if not notice_group_id or getattr(config, 'expire_notice_sent_at', None):
            return False
        if source_type == WorkbenchTodoSourceTypeEnum.UI_AUTH.value:
            if config.refresh_mode != UiAuthRefreshModeEnum.EXPIRE_NOTICE.value:
                return False
            from src.apps.auto_ui.services.ui_auth import UiAuthManager

            auth_manager = UiAuthManager
        elif source_type == WorkbenchTodoSourceTypeEnum.API_AUTH.value:
            if config.refresh_mode != ApiAuthRefreshModeEnum.EXPIRE_NOTICE.value:
                return False
            from src.apps.auto_api.services.base.api_base_test_setup.auth_manager import (
                ApiAuthManager,
            )

            auth_manager = ApiAuthManager
        else:
            return False
        sent_at = timezone.now()
        if not auth_manager.claim_expire_notice(config.id, sent_at):
            return False
        try:
            NoticeMain(notice_group_id).notice_monitoring(
                f'授权风险提醒\n- {title}\n- {summary}'
            )
            return True
        except Exception as error:
            auth_manager.release_expire_notice(config.id)
            log.system.error(
                f'发送授权风险通知组提醒失败：source_type={source_type}，'
                f'config_id={config.id}，error={error}'
            )
            return False

    @classmethod
    def reconcile_auth_todos(cls) -> dict:
        ui_count = 0
        api_count = 0
        active_event_keys = set()
        ui_configs = UiAuthConfig.objects.select_related('project_product').filter(
            status=StatusEnum.SUCCESS.value,
        ).filter(
            Q(last_refresh_status=UiAuthRefreshStatusEnum.FAIL.value)
            | Q(
                refresh_mode=UiAuthRefreshModeEnum.MANUAL.value,
                last_refresh_time__isnull=False,
            )
            | Q(
                refresh_mode=UiAuthRefreshModeEnum.EXPIRE_NOTICE.value,
                expires_at__isnull=False,
            )
        )
        for config in ui_configs:
            if config.last_refresh_status == UiAuthRefreshStatusEnum.FAIL.value:
                todo = cls._record_auth_failure(
                    config,
                    WorkbenchTodoSourceTypeEnum.UI_AUTH.value,
                    '前端授权',
                )
                if todo:
                    active_event_keys.add(todo.event_key)
                    ui_count += 1
            todo = cls._record_auth_expiry(
                config,
                WorkbenchTodoSourceTypeEnum.UI_AUTH.value,
                '前端授权',
                UiAuthRefreshModeEnum.MANUAL.value,
            )
            if todo:
                active_event_keys.add(todo.event_key)
                ui_count += 1

        api_configs = ApiAuthConfig.objects.select_related('project_product').filter(
            status=StatusEnum.SUCCESS.value,
        ).filter(
            Q(last_refresh_status=ApiAuthRefreshStatusEnum.FAIL.value)
            | Q(
                refresh_mode=ApiAuthRefreshModeEnum.MANUAL.value,
                last_refresh_time__isnull=False,
            )
            | Q(
                refresh_mode=ApiAuthRefreshModeEnum.EXPIRE_NOTICE.value,
                expires_at__isnull=False,
            )
        )
        for config in api_configs:
            if config.last_refresh_status == ApiAuthRefreshStatusEnum.FAIL.value:
                todo = cls._record_auth_failure(
                    config,
                    WorkbenchTodoSourceTypeEnum.API_AUTH.value,
                    '服务授权',
                )
                if todo:
                    active_event_keys.add(todo.event_key)
                    api_count += 1
            todo = cls._record_auth_expiry(
                config,
                WorkbenchTodoSourceTypeEnum.API_AUTH.value,
                '服务授权',
                ApiAuthRefreshModeEnum.MANUAL.value,
            )
            if todo:
                active_event_keys.add(todo.event_key)
                api_count += 1

        pending_auth_todos = WorkbenchTodo.objects.filter(
            source_type__in=[
                WorkbenchTodoSourceTypeEnum.UI_AUTH.value,
                WorkbenchTodoSourceTypeEnum.API_AUTH.value,
            ],
        )
        if active_event_keys:
            pending_auth_todos = pending_auth_todos.exclude(event_key__in=active_event_keys)
        resolved_count = cls._resolve_queryset(
            pending_auth_todos,
            '系统自动检测：授权风险已解除或授权配置已停用。',
        )
        return {
            'ui_auth_todo_count': ui_count,
            'api_auth_todo_count': api_count,
            'resolved_auth_todo_count': resolved_count,
        }

    @classmethod
    def record_data_factory_schema_issue(
            cls,
            entity: DataFactoryEntity,
            *,
            differences: list,
            invalidated_template_count: int,
            review_only: bool = False,
    ):
        occurred_at = timezone.now()
        event_type = (
            WorkbenchTodoEventTypeEnum.DATA_FACTORY_SCHEMA_REVIEW.value
            if review_only
            else WorkbenchTodoEventTypeEnum.DATA_FACTORY_SCHEMA_INVALID.value
        )
        difference_key = cls._timestamp_key(getattr(entity, 'update_time', None) or occurred_at)
        difference_fingerprint = cls._schema_difference_fingerprint(differences)
        event_key = f'data-factory:{entity.id}:schema:{event_type}:{difference_key}'
        return cls._upsert(event_key, {
            'source_type': WorkbenchTodoSourceTypeEnum.DATA_FACTORY_ENTITY.value,
            'event_type': event_type,
            'source_id': entity.id,
            'project_product_id': entity.project_product_id,
            'module_id': entity.module_id,
            'severity': (
                WorkbenchTodoSeverityEnum.WARNING.value
                if review_only
                else WorkbenchTodoSeverityEnum.DANGER.value
            ),
            'title': (
                f'数据模型结构待确认：{entity.name}'
                if review_only
                else f'数据模型已失效：{entity.name}'
            ),
            'summary': (
                '扫描发现数据库表结构变化，批量保护已阻止自动停用，请人工确认。'
                if review_only
                else f'数据库表结构发生不兼容变化，已停用模型并影响 {invalidated_template_count} 个模板。'
            ),
            'due_at': occurred_at,
            'occurred_at': occurred_at,
            'details': {
                'source_name': '数据工厂模型',
                'entity_name': entity.name,
                'table_name': entity.table_name,
                'datasource_alias_id': entity.datasource_alias_id,
                'invalidated_template_count': invalidated_template_count,
                'differences': differences,
                'difference_fingerprint': difference_fingerprint,
            },
        })

    @classmethod
    def resolve_data_factory_review_todos(
            cls,
            *,
            scanned_entity_ids: set[int],
            active_entity_ids: set[int],
    ) -> int:
        if not scanned_entity_ids:
            return 0
        queryset = WorkbenchTodo.objects.filter(
            source_type=WorkbenchTodoSourceTypeEnum.DATA_FACTORY_ENTITY.value,
            event_type=WorkbenchTodoEventTypeEnum.DATA_FACTORY_SCHEMA_REVIEW.value,
            source_id__in=scanned_entity_ids,
        )
        if active_entity_ids:
            queryset = queryset.exclude(source_id__in=active_entity_ids)
        return cls._resolve_queryset(
            queryset,
            '系统自动检测：最新表结构扫描已确认该待核验风险不再存在。',
        )

    @classmethod
    def reconcile_data_factory_todos(cls) -> dict:
        pending_todos = WorkbenchTodo.objects.filter(
            source_type=WorkbenchTodoSourceTypeEnum.DATA_FACTORY_ENTITY.value,
            status=WorkbenchTodoStatusEnum.PENDING.value,
        )
        source_ids = set(pending_todos.values_list('source_id', flat=True))
        entities = {
            entity.id: entity
            for entity in DataFactoryEntity.objects.filter(id__in=source_ids).only(
                'id', 'status', 'status_change_reason_code'
            )
        }
        active_invalid_ids = {
            entity_id
            for entity_id, entity in entities.items()
            if entity.status == StatusEnum.FAIL.value
               and entity.status_change_reason_code in {'schema_incompatible', 'schema_changed'}
        }
        invalid_queryset = pending_todos.filter(
            event_type=WorkbenchTodoEventTypeEnum.DATA_FACTORY_SCHEMA_INVALID.value,
        )
        if active_invalid_ids:
            invalid_queryset = invalid_queryset.exclude(source_id__in=active_invalid_ids)
        resolved_invalid_count = cls._resolve_queryset(
            invalid_queryset,
            '系统自动检测：数据模型已恢复有效或原模型已删除。',
        )

        resolved_review_entity_ids = (source_ids - set(entities)) | {
            entity_id
            for entity_id, entity in entities.items()
            if entity.status != StatusEnum.SUCCESS.value
        }
        resolved_review_count = 0
        if resolved_review_entity_ids:
            resolved_review_count = cls._resolve_queryset(
                pending_todos.filter(
                    event_type=WorkbenchTodoEventTypeEnum.DATA_FACTORY_SCHEMA_REVIEW.value,
                    source_id__in=resolved_review_entity_ids,
                ),
                '系统自动检测：数据模型已停用或删除，原待核验风险已结束。',
            )
        return {
            'resolved_data_factory_invalid_count': resolved_invalid_count,
            'resolved_data_factory_review_count': resolved_review_count,
        }

    @classmethod
    def reconcile_api_case_prepublication_todos(
            cls,
            *,
            project_product_ids: set[int] | None = None,
    ) -> dict:
        """每个产品聚合一条预发布审核待办，数量变化时复用原记录。"""
        releases = ApiCaseRelease.objects.filter(
            status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value,
        )
        if project_product_ids is not None:
            if not project_product_ids:
                return {
                    'api_case_prepublication_todo_count': 0,
                    'resolved_api_case_prepublication_todo_count': 0,
                }
            releases = releases.filter(
                api_case__project_product_id__in=project_product_ids,
            )
        release_rows = releases.values(
            'api_case__project_product_id',
            'api_case_id',
            'api_case__name',
            'api_case__module_id',
            'api_case__module__name',
            'revision_id',
            'revision__revision_no',
            'create_time',
        ).order_by('api_case__project_product_id', 'create_time', 'id')

        grouped: dict[int, dict] = {}
        for row in release_rows.iterator(chunk_size=500):
            project_product_id = row['api_case__project_product_id']
            group = grouped.setdefault(
                project_product_id,
                {
                    'occurred_at': row['create_time'],
                    'cases': [],
                },
            )
            group['cases'].append({
                'case_id': row['api_case_id'],
                'case_name': row['api_case__name'],
                'module_id': row['api_case__module_id'],
                'module_name': row['api_case__module__name'],
                'revision_id': row['revision_id'],
                'revision_no': row['revision__revision_no'],
                'submitted_at': row['create_time'].isoformat(),
            })

        active_event_keys = set()
        for project_product_id, group in grouped.items():
            cases = group['cases']
            count = len(cases)
            event_key = f'api-case:prepublication:product:{project_product_id}'
            active_event_keys.add(event_key)
            cls._upsert(
                event_key,
                {
                    'source_type': WorkbenchTodoSourceTypeEnum.API_CASE.value,
                    'event_type': (
                        WorkbenchTodoEventTypeEnum.API_CASE_PREPUBLICATION_REVIEW.value
                    ),
                    'source_id': project_product_id,
                    'project_product_id': project_product_id,
                    'module_id': None,
                    'severity': WorkbenchTodoSeverityEnum.WARNING.value,
                    'title': 'API Case 预发布待审核',
                    'summary': f'当前有 {count} 个 API Case 处于预发布状态，请审核通过或退回未发布。',
                    'due_at': group['occurred_at'],
                    'occurred_at': group['occurred_at'],
                    'details': {
                        'source_name': 'API Case 预发布',
                        'prepublication_count': count,
                        'cases': cases[:cls.API_CASE_PREPUBLICATION_PREVIEW_LIMIT],
                        'case_preview_truncated': (
                                count > cls.API_CASE_PREPUBLICATION_PREVIEW_LIMIT
                        ),
                    },
                },
                notify_owner=False,
            )

        stale_todos = WorkbenchTodo.objects.filter(
            source_type=WorkbenchTodoSourceTypeEnum.API_CASE.value,
            event_type=WorkbenchTodoEventTypeEnum.API_CASE_PREPUBLICATION_REVIEW.value,
        )
        if project_product_ids is not None:
            stale_todos = stale_todos.filter(source_id__in=project_product_ids)
        if active_event_keys:
            stale_todos = stale_todos.exclude(event_key__in=active_event_keys)
        resolved_count = cls._resolve_queryset(
            stale_todos,
            '系统自动检测：该产品已无待审核的预发布 API Case。',
        )
        return {
            'api_case_prepublication_todo_count': len(grouped),
            'resolved_api_case_prepublication_todo_count': resolved_count,
        }

    @classmethod
    def _cleanup_items(cls, execution: DataFactoryExecution) -> list[DataFactoryExecutionItem]:
        prefetched_items = getattr(execution, 'workbench_cleanup_items', None)
        if prefetched_items is not None:
            return prefetched_items
        return list(
            DataFactoryExecutionItem.objects.select_related(
                'database',
                'datasource_binding__database',
                'template__entity',
            ).filter(execution_id=execution.id).order_by('id')
        )

    @classmethod
    def record_data_factory_cleanup_failure(cls, execution: DataFactoryExecution):
        from src.apps.data_factory.services.execution_snapshot import get_insert_snapshot

        if execution.cleanup_status != DataFactoryCleanupStatusEnum.FAIL.value:
            return None
        occurred_at = execution.cleanup_time or execution.update_time or timezone.now()
        items = cls._cleanup_items(execution)
        failed_items = [
            item for item in items
            if item.cleanup_status == DataFactoryCleanupStatusEnum.FAIL.value
        ]
        success_count = sum(
            item.cleanup_status == DataFactoryCleanupStatusEnum.SUCCESS.value
            for item in items
        )
        skipped_count = sum(
            item.cleanup_status == DataFactoryCleanupStatusEnum.SKIPPED.value
            for item in items
        )
        errors = []
        for item in failed_items[:10]:
            binding = getattr(item, 'datasource_binding', None)
            database = getattr(item, 'database', None) or (
                getattr(binding, 'database', None) if binding else None
            )
            template = getattr(item, 'template', None)
            entity = getattr(template, 'entity', None) if template else None
            storage_snapshot = get_insert_snapshot(item)
            environment = getattr(binding, 'environment', None) if binding else None
            errors.append({
                'item_id': item.id,
                'alias': item.alias,
                'database_id': getattr(database, 'id', None),
                'database_name': (
                        getattr(database, 'display_name', None)
                        or getattr(database, 'name', None)
                ),
                'environment': environment,
                'environment_name': (
                    EnvironmentEnum.get_value(environment) if environment is not None else None
                ),
                'table_name': storage_snapshot.get('table_name') or getattr(entity, 'table_name', None),
                'primary_key': storage_snapshot.get('primary_key') or getattr(entity, 'primary_key', None),
                'primary_value': getattr(item, 'primary_value', None),
                'cleanup_time': (
                    cls._format_datetime(item.cleanup_time)
                    if getattr(item, 'cleanup_time', None)
                    else cls._format_datetime(occurred_at)
                ),
                'error': (item.cleanup_error or '清理失败')[:500],
            })
        event_key = (
            f'data-factory:execution:{execution.id}:cleanup-failed:'
            f'{cls._timestamp_key(occurred_at)}'
        )
        return cls._upsert(event_key, {
            'source_type': WorkbenchTodoSourceTypeEnum.DATA_FACTORY_EXECUTION.value,
            'event_type': WorkbenchTodoEventTypeEnum.DATA_FACTORY_CLEANUP_FAILED.value,
            'source_id': execution.id,
            'project_product_id': execution.project_product_id,
            'module_id': execution.module_id,
            'severity': WorkbenchTodoSeverityEnum.DANGER.value,
            'title': f'数据工厂清理失败：{execution.execution_no}',
            'summary': (
                f'清理失败 {len(failed_items)} 项、成功 {success_count} 项、'
                f'跳过 {skipped_count} 项，请检查失败明细后重试。'
            ),
            'due_at': occurred_at,
            'occurred_at': occurred_at,
            'details': {
                'source_name': '数据工厂执行记录',
                'execution_no': execution.execution_no,
                'template_name': execution.template.name if execution.template_id else None,
                'failed_count': len(failed_items),
                'success_count': success_count,
                'skipped_count': skipped_count,
                'total_count': len(items),
                'errors': errors,
            },
        })

    @classmethod
    def resolve_data_factory_cleanup_todos(cls, execution_id: int) -> int:
        return cls._resolve_queryset(
            WorkbenchTodo.objects.filter(
                source_type=WorkbenchTodoSourceTypeEnum.DATA_FACTORY_EXECUTION.value,
                event_type__in=[
                    WorkbenchTodoEventTypeEnum.DATA_FACTORY_CLEANUP_REQUIRED.value,
                    WorkbenchTodoEventTypeEnum.DATA_FACTORY_CLEANUP_FAILED.value,
                ],
                source_id=execution_id,
            ),
            '系统自动检测：该执行已不满足清理失败待办条件；待手动清理请在执行记录中处理。',
        )

    @classmethod
    def resolve_data_factory_cleanup_required_todos(cls, execution_id: int) -> int:
        return cls._resolve_queryset(
            WorkbenchTodo.objects.filter(
                source_type=WorkbenchTodoSourceTypeEnum.DATA_FACTORY_EXECUTION.value,
                event_type=WorkbenchTodoEventTypeEnum.DATA_FACTORY_CLEANUP_REQUIRED.value,
                source_id=execution_id,
            ),
            '系统自动检测：待手动清理不再生成待办，请在数据工厂执行记录中处理。',
        )

    @classmethod
    def reconcile_data_factory_cleanup_todos(cls) -> dict:
        cleanup_executions = DataFactoryExecution.objects.select_related(
            'template',
            'project_product',
            'module',
        ).filter(
            cleanup_status=DataFactoryCleanupStatusEnum.FAIL.value,
        ).prefetch_related(
            Prefetch(
                'datafactoryexecutionitem_set',
                queryset=DataFactoryExecutionItem.objects.select_related(
                    'database',
                    'datasource_binding__database',
                    'template__entity',
                ).order_by('id'),
                to_attr='workbench_cleanup_items',
            ),
        )
        active_event_keys = set()
        created_count = 0
        for execution in cleanup_executions:
            todo = cls.record_data_factory_cleanup_failure(execution)
            if todo:
                active_event_keys.add(todo.event_key)
                created_count += 1

        stale_todos = WorkbenchTodo.objects.filter(
            source_type=WorkbenchTodoSourceTypeEnum.DATA_FACTORY_EXECUTION.value,
            event_type__in=[
                WorkbenchTodoEventTypeEnum.DATA_FACTORY_CLEANUP_REQUIRED.value,
                WorkbenchTodoEventTypeEnum.DATA_FACTORY_CLEANUP_FAILED.value,
            ],
        )
        if active_event_keys:
            stale_todos = stale_todos.exclude(event_key__in=active_event_keys)
        resolved_count = cls._resolve_queryset(
            stale_todos,
            '系统自动检测：该执行已不满足清理失败待办条件；待手动清理请在执行记录中处理。',
        )
        return {
            'data_factory_cleanup_todo_count': created_count,
            'resolved_data_factory_cleanup_todo_count': resolved_count,
        }

    @classmethod
    def reconcile_todos(cls) -> dict:
        with cls._reconcile_lock() as acquired:
            if not acquired:
                log.system.info('首页风险待办已有其他进程正在对账，本次跳过')
                return {'reconciliation_skipped': True}
            return {
                **cls.reconcile_auth_todos(),
                **cls.reconcile_data_factory_todos(),
                **cls.reconcile_data_factory_cleanup_todos(),
                **cls.reconcile_api_case_prepublication_todos(),
            }

    @classmethod
    def reconcile_auth_risk_todos(cls) -> dict:
        with cls._reconcile_lock() as acquired:
            if not acquired:
                log.system.info('授权风险代办同步已有其他进程正在执行，本次跳过')
                return {'reconciliation_skipped': True}
            return cls.reconcile_auth_todos()

    @classmethod
    def reconcile_non_auth_todos(cls) -> dict:
        with cls._reconcile_lock() as acquired:
            if not acquired:
                log.system.info('首页非授权风险待办已有其他进程正在对账，本次跳过')
                return {'reconciliation_skipped': True}
            return {
                **cls.reconcile_data_factory_todos(),
                **cls.reconcile_data_factory_cleanup_todos(),
                **cls.reconcile_api_case_prepublication_todos(),
            }

    @classmethod
    def visible_queryset(cls, user):
        queryset = WorkbenchTodo.objects.select_related(
            'project_product',
            'project_product__project',
            'module',
            'handled_by',
        ).exclude(
            event_type=WorkbenchTodoEventTypeEnum.DATA_FACTORY_CLEANUP_REQUIRED.value,
            status=WorkbenchTodoStatusEnum.PENDING.value,
        ).prefetch_related(
            'project_product__owners',
        )
        if user is None:
            return queryset.none()
        if PermissionMenuService.is_effective_super_admin(user):
            return queryset
        allowed_ids = ProjectProductScopeService.strict_project_product_ids_for_user(user)
        owner_scope = Q(project_product__owners=user)
        if allowed_ids:
            return queryset.filter(
                owner_scope
                | (
                        ~Q(
                            event_type=(
                                WorkbenchTodoEventTypeEnum.API_CASE_PREPUBLICATION_REVIEW.value
                            )
                        )
                        & Q(project_product_id__in=allowed_ids)
                )
            ).distinct()
        return queryset.filter(owner_scope).distinct()

    @staticmethod
    def _owners(todo: WorkbenchTodo) -> list:
        owners_relation = getattr(todo.project_product, 'owners', None)
        if owners_relation is not None:
            owners = list(
                owners_relation.all()
                if hasattr(owners_relation, 'all')
                else owners_relation
            )
            if owners:
                return owners
        return []

    @classmethod
    def _owner_payloads(cls, todo: WorkbenchTodo) -> list[dict]:
        return [
            {
                'id': owner.id,
                'name': owner.name,
                'username': owner.username,
            }
            for owner in cls._owners(todo)
        ]

    @staticmethod
    def _notification_url() -> str:
        domain = SystemConfigService.get(CacheDataKeyEnum.SYSTEM_DOMAIN_NAME.name, default='')
        return f"{str(domain).strip().rstrip('/')}/#/index" if domain else ''

    @classmethod
    def _notify_owner(cls, todo: WorkbenchTodo) -> bool:
        sent = False
        for owner in cls._owners(todo):
            if not UserCredentialService.is_valid_email(owner.username):
                continue
            try:
                platform_name = SystemConfigService.get_platform_name()
                safe_platform_name = html.escape(platform_name)
                email = UserCredentialService.normalize_email(owner.username)
                owner_name = html.escape(owner.name or email)
                title = html.escape(todo.title)
                summary = html.escape(todo.summary or '')
                project_name = html.escape(todo.project_product.project.name)
                product_name = html.escape(todo.project_product.name)
                todo_url = cls._notification_url()
                link_content = (
                    f'<p><a href="{html.escape(todo_url, quote=True)}">打开{safe_platform_name}查看待办</a></p>'
                    if todo_url
                    else ''
                )
                content = f"""<!doctype html>
<html>
<body style="font-family: Arial, sans-serif; color: #1d2129; line-height: 1.7;">
  <h2>{safe_platform_name}待办提醒</h2>
  <p>{owner_name}，您好：</p>
  <p>您负责的项目产品 <strong>{project_name} / {product_name}</strong> 产生了新的待办：</p>
  <p><strong>{title}</strong></p>
  <p>{summary}</p>
  {link_content}
</body>
</html>"""
                UserCredentialService.send_email(
                    email=email,
                    subject=f'{platform_name}待办提醒：{todo.title}',
                    content=content,
                )
                sent = True
            except Exception as error:
                log.system.error(
                    f'发送工作台待办邮件失败，不影响待办创建：todo_id={getattr(todo, "id", None)}，'
                    f'owner_id={getattr(owner, "id", None)}，error={error}'
                )
        return sent

    @classmethod
    def serialize(cls, todo: WorkbenchTodo) -> dict:
        return {
            'id': todo.id,
            'source_type': todo.source_type,
            'source_type_name': WorkbenchTodoSourceTypeEnum.get_value(todo.source_type),
            'event_type': todo.event_type,
            'event_type_name': WorkbenchTodoEventTypeEnum.get_value(todo.event_type),
            'source_id': todo.source_id,
            'severity': todo.severity,
            'severity_name': WorkbenchTodoSeverityEnum.get_value(todo.severity),
            'status': todo.status,
            'status_name': WorkbenchTodoStatusEnum.get_value(todo.status),
            'title': todo.title,
            'summary': todo.summary,
            'due_at': todo.due_at.strftime('%Y-%m-%d %H:%M:%S') if todo.due_at else None,
            'occurred_at': todo.occurred_at.strftime('%Y-%m-%d %H:%M:%S'),
            'project_product': {
                'id': todo.project_product_id,
                'name': todo.project_product.name,
                'project': {
                    'id': todo.project_product.project_id,
                    'name': todo.project_product.project.name,
                },
            },
            'module': (
                {'id': todo.module_id, 'name': todo.module.name}
                if todo.module_id and todo.module
                else None
            ),
            'details': todo.details,
            'owners': cls._owner_payloads(todo),
            'handled_by': (
                {'id': todo.handled_by_id, 'name': todo.handled_by.name}
                if todo.handled_by_id and todo.handled_by
                else None
            ),
            'handled_at': (
                todo.handled_at.strftime('%Y-%m-%d %H:%M:%S') if todo.handled_at else None
            ),
            'handle_note': todo.handle_note,
            'can_mark_handled': cls.can_mark_handled(todo),
        }

    @classmethod
    def summary(cls, queryset) -> dict:
        counts = {
            row['event_type']: row['count']
            for row in queryset.filter(status=WorkbenchTodoStatusEnum.PENDING.value)
            .values('event_type')
            .annotate(count=Count('id'))
        }
        return {
            'pending': sum(counts.values()),
            'expiring': counts.get(WorkbenchTodoEventTypeEnum.AUTH_EXPIRING.value, 0),
            'expired': counts.get(WorkbenchTodoEventTypeEnum.AUTH_EXPIRED.value, 0),
            'refresh_failed': counts.get(WorkbenchTodoEventTypeEnum.AUTH_REFRESH_FAILED.value, 0),
            'schema_invalid': counts.get(WorkbenchTodoEventTypeEnum.DATA_FACTORY_SCHEMA_INVALID.value, 0),
            'schema_review': counts.get(WorkbenchTodoEventTypeEnum.DATA_FACTORY_SCHEMA_REVIEW.value, 0),
            'cleanup_failed': counts.get(
                WorkbenchTodoEventTypeEnum.DATA_FACTORY_CLEANUP_FAILED.value,
                0,
            ),
            'cleanup_required': counts.get(
                WorkbenchTodoEventTypeEnum.DATA_FACTORY_CLEANUP_REQUIRED.value,
                0,
            ),
            'api_case_prepublication_review': counts.get(
                WorkbenchTodoEventTypeEnum.API_CASE_PREPUBLICATION_REVIEW.value,
                0,
            ),
        }
