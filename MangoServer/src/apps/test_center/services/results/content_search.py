"""有界、可取消的执行内容检索，不使用业务执行队列。"""
import json
import re
import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time as day_time, timedelta

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import close_old_connections
from django.utils import timezone
from pydantic import ValidationError

from src.apps.data_factory.selectors.execution_audit import ExecutionAuditSelector
from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum
from src.apps.system.services.runtime_kv.store import RuntimeKV
from src.apps.test_center.enums.content_search import ContentSearchKindEnum as Kind, ContentSearchStatusEnum as Status
from src.apps.test_center.exceptions import (
    TestCenterError, EXECUTION_SEARCH_INVALID, EXECUTION_SEARCH_DENIED, EXECUTION_SEARCH_BUSY,
)
from src.apps.test_center.schemas.content_search import ContentSearchQuery, ContentSearchTask, ContentSearchHit
from src.apps.test_center.selectors.execution_result import ExecutionResultAccessSelector
from src.apps.test_center.services.results.result_file import ExecutionResultFileService
from src.apps.user.selectors.querysets import UserQuerySelector
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService
from src.common.logging import log


class ExecutionContentSearchService:
    MAX_FILE_BYTES = 20 * 1024 * 1024
    PAGE_SIZE = 20
    TTL = 86400
    LEASE_TTL = 180
    _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='execution-content-search')
    _slot = threading.Lock()

    @staticmethod
    def store():
        return RuntimeKV.namespace(RuntimeKVNamespaceEnum.EXECUTION_SEARCH)

    @staticmethod
    def authorize(user, product_id):
        if user is None:
            raise TestCenterError(EXECUTION_SEARCH_DENIED)
        if product_id is not None:
            if not ProjectProductScopeService.has_project_product(user, product_id):
                raise TestCenterError(EXECUTION_SEARCH_DENIED)
            return [product_id]
        if PermissionMenuService.is_effective_super_admin(user):
            return None
        if ProjectProductScopeService.can_view_all_project_data(user):
            from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
            return list(TestCenterQuerySelector.project_product().values_list('id', flat=True))
        return sorted(ProjectProductScopeService.project_product_ids_for_user(user))

    @classmethod
    def authorize_task(cls, user, task):
        current = cls.authorize(user, task.query.project_product_id)
        frozen = [task.query.project_product_id] if task.query.project_product_id is not None else task.product_scope
        if current is not None and (frozen is None or not set(frozen) <= set(current)):
            raise TestCenterError(EXECUTION_SEARCH_DENIED)

    @classmethod
    def start(cls, user, kind, payload):
        try:
            query = ContentSearchQuery.model_validate(payload)
        except ValidationError as error:
            raise TestCenterError(EXECUTION_SEARCH_INVALID) from error
        product_scope = cls.authorize(user, query.project_product_id)
        if kind not in Kind.get_key_list():
            raise TestCenterError(EXECUTION_SEARCH_INVALID)
        store = cls.store()
        task_id = uuid.uuid4().hex
        acquired, lease_version = store.set_if_absent('active', {'task_id': task_id}, ttl=cls.LEASE_TTL)
        if not acquired:
            raise TestCenterError(EXECUTION_SEARCH_BUSY)
        if not cls._slot.acquire(blocking=False):
            store.delete_if_version('active', lease_version)
            raise TestCenterError(EXECUTION_SEARCH_BUSY)
        now = time.time()
        task = ContentSearchTask(task_id=task_id, owner_id=user.id, kind=kind, query=query,
                                 product_scope=product_scope, started_at=now, updated_at=now)
        try:
            cls.save(task)
            initial = cls.present(task.model_copy(deep=True), 1)
            cls._executor.submit(cls.run, task, lease_version)
        except Exception:
            try:
                store.delete_if_version('active', lease_version)
            finally:
                cls._slot.release()
            raise
        return initial

    @classmethod
    def save(cls, task):
        task.updated_at = time.time()
        cls.store().set(f'task:{task.task_id}', task.model_dump(mode='json'), ttl=cls.TTL)

    @classmethod
    def save_page(cls, task):
        if task.items:
            page = (task.match_count - 1) // cls.PAGE_SIZE + 1
            cls.store().set(f'hits:{task.task_id}:{page}',
                            {'items': [hit.model_dump(mode='json') for hit in task.items]}, ttl=cls.TTL)

    @classmethod
    def owned(cls, user, kind, task_id):
        if not isinstance(task_id, str) or len(task_id) != 32 or any(c not in '0123456789abcdef' for c in task_id):
            raise TestCenterError(EXECUTION_SEARCH_DENIED)
        raw = cls.store().get(f'task:{task_id}')
        if not raw or raw.get('version') != 2:
            raise TestCenterError(EXECUTION_SEARCH_DENIED)
        task = ContentSearchTask.model_validate(raw, context={'persisted': True})
        if user is None or task.owner_id != user.id or task.kind != kind:
            raise TestCenterError(EXECUTION_SEARCH_DENIED)
        cls.authorize_task(user, task)
        return task

    @classmethod
    def get(cls, user, kind, task_id, page=1):
        task = cls.owned(user, kind, task_id)
        if (task.status == Status.RUNNING.value and time.time() - task.updated_at > cls.LEASE_TTL
                and cls.store().get('active') != {'task_id': task.task_id}):
            task.status = Status.PARTIAL.value
            task.message = '检索进程已中断，请重新检索'
        return cls.present(task, page)

    @classmethod
    def cancel(cls, user, kind, task_id):
        task = cls.owned(user, kind, task_id)
        if task.status == Status.RUNNING.value:
            cls.store().set(f'cancel:{task_id}', True, ttl=cls.TTL)
        return cls.present(task, 1)

    @classmethod
    def present(cls, task, page):
        try:
            page = int(page)
        except (TypeError, ValueError) as error:
            raise TestCenterError(EXECUTION_SEARCH_INVALID) from error
        if page < 1:
            raise TestCenterError(EXECUTION_SEARCH_INVALID)
        raw_page = cls.store().get(f'hits:{task.task_id}:{page}') if task.match_count else None
        published = min(cls.PAGE_SIZE, max(0, task.match_count - (page - 1) * cls.PAGE_SIZE))
        hits = [ContentSearchHit.model_validate(row) for row in (raw_page or {}).get('items', [])[:published]]
        names = ExecutionResultAccessSelector.search_names(task.query.project_product_id, hits,
                                                          product_ids=task.product_scope) if hits else {}
        result = task.model_dump(mode='json', exclude={'items', 'owner_id', 'product_scope'})
        if task.match_count and page <= (task.match_count - 1) // cls.PAGE_SIZE + 1 and raw_page is None:
            result.update(message='部分检索结果已过期，请重新检索')
            if task.status != Status.RUNNING.value:
                result['status'] = Status.PARTIAL.value
        result.update(items=[dict(hit.model_dump(), name=hit.name or names.get((hit.target_type, hit.target_id), ''))
                             for hit in hits], count=task.match_count, page=page, page_size=cls.PAGE_SIZE)
        return result

    @staticmethod
    def bounds(task):
        start = datetime.combine(task.query.day, day_time.min)
        if settings.USE_TZ:
            start = timezone.make_aware(start, timezone.get_current_timezone())
        end = min(start + timedelta(days=1), datetime.fromtimestamp(task.started_at, start.tzinfo))
        return start, end

    @staticmethod
    def match(payload, keyword):
        """只返回一个命中片段；凭据字段不搜索、不回传。"""
        stack = [iter([('', payload)])]
        while stack:
            try:
                path, value = next(stack[-1])
            except StopIteration:
                stack.pop()
                continue
            if isinstance(value, dict):
                if ('value' in value or 'values' in value) and re.search(r'authorization|cookie|password|passwd|token|secret|api[-_]?key|signature|credential',
                             str(value.get('key') or value.get('name') or ''), re.I):
                    continue
                stack.append(ExecutionContentSearchService.children(path, value))
            elif isinstance(value, list):
                stack.append(ExecutionContentSearchService.children(path, value))
            elif value is not None:
                text = str(value)
                if isinstance(value, str) and text.lstrip().startswith(('{', '[')):
                    try:
                        stack.append(iter([(path, json.loads(text))]))
                        continue
                    except (ValueError, TypeError):
                        pass
                text = re.sub(r'(?i)Bearer\s+[^\s"<>]+', 'Bearer [已脱敏]', text)
                text = re.sub(r'''(?i)(["']?(?:authorization|cookie|password|passwd|secret|token|api[-_]?key|signature|credential)["']?\s*[=:]\s*)(?:"[^"]*"|'[^']*'|[^,\s&<>}]+)''', r'\1[已脱敏]', text)
                pos = text.casefold().find(keyword.casefold())
                if pos >= 0:
                    return (path[:200], text[max(0, pos - 60):pos + len(keyword) + 100]), False
        return None, False

    @staticmethod
    def children(path, value):
        mapping = isinstance(value, dict)
        for key, item in value.items() if mapping else enumerate(value):
            if mapping and re.search(r'authorization|cookie|password|passwd|token|secret|api[-_]?key|signature|credential', str(key), re.I):
                continue
            child_path = (f'{path}.{key}' if path else str(key)) if mapping else f'{path}[{key}]'
            yield child_path[:200], item

    @classmethod
    def payload(cls, task, row):
        if task.kind == Kind.DATASOURCE.value:
            text = ExecutionAuditSelector.search_payload(row.id, cls.MAX_FILE_BYTES)
            size = len((text or '').encode('utf-8'))
            task.read_bytes += size
            if size > cls.MAX_FILE_BYTES:
                return None, size, True
            return json.loads(text) if text else None, size, row.result_truncated or text is None
        if row.result_cleaned:
            return None, 0, True
        if row.result_size > cls.MAX_FILE_BYTES:
            return None, 0, True
        if row.result_object_key:
            limit = cls.MAX_FILE_BYTES
            try:
                raw = ExecutionResultFileService.read(default_storage.open(row.result_object_key, 'rb'), limit=limit)
            except Exception:
                # 失败读取可能已消耗部分解压预算，按本次上限保守计费，避免损坏文件绕过预算。
                task.read_bytes += limit + 1
                raise
            task.read_bytes += len(raw)
            if len(raw) > cls.MAX_FILE_BYTES:
                return None, len(raw), True
            return json.loads(raw), len(raw), False
        text = ExecutionResultAccessSelector.inline_search_payload(row.id, cls.MAX_FILE_BYTES)
        size = len((text or '').encode('utf-8'))
        task.read_bytes += size
        if size > cls.MAX_FILE_BYTES:
            return None, size, True
        return json.loads(text) if text else None, size, text is None

    @staticmethod
    def hit(task, row, match):
        if task.kind == Kind.AUTOMATION.value:
            detail = row.test_suite_detail
            return ContentSearchHit(record_id=row.id, target_type=row.target_type, target_id=row.target_id,
                name=(getattr(detail, 'case_name', None) or '')[:160], create_time=str(row.create_time),
                source_type=row.source_type, report_id=row.test_suite_id,
                trigger_user=row.trigger_user.name if row.trigger_user else '', path=match[0], snippet=match[1])
        source = row.source_detail or {}
        case_id = source.get('case_id')
        kind = row.source_type
        if kind in ('api_case', 'api_case_parameter', 'api_global_variable', 'api_custom_code', 'api_case_resource'):
            original_kind = kind
            kind = 'api_case' if case_id or original_kind == 'api_case' else kind
        if kind == 'api_case':
            case_id = case_id or row.source_id
        elif kind == 'data_factory':
            from src.apps.data_factory.enums.execution import DataFactoryExecutionSourceEnum
            source_type = source.get('case_source_type')
            kind = {DataFactoryExecutionSourceEnum.API_CASE.value: 'api_case',
                    DataFactoryExecutionSourceEnum.UI_CASE.value: 'ui_case'}.get(source_type, kind)
            if kind in ('api_case', 'ui_case'):
                case_id = case_id or source.get('case_source_id')
        return ContentSearchHit(record_id=row.id, target_type=kind, target_id=case_id or row.source_id,
            name=str(source.get('case_name') or '')[:160], create_time=str(row.create_time),
            source_type=row.source_type, stage=row.source_stage, report_id=source.get('test_suite_id'),
            path=match[0], snippet=match[1])

    @classmethod
    def run(cls, task, lease_version):
        close_old_connections()
        cursor = None
        checked_at = 0
        renewed_at = time.monotonic()
        saved_at = renewed_at
        store = cls.store()
        try:
            start, end = cls.bounds(task)
            while True:
                user = UserQuerySelector.user().select_related('role').get(id=task.owner_id)
                cls.authorize_task(user, task)
                selector = ExecutionResultAccessSelector if task.kind == Kind.AUTOMATION.value else ExecutionAuditSelector
                rows = selector.search_batch(task.query, start, end, cursor, product_ids=task.product_scope)
                if not rows:
                    task.status = Status.PARTIAL.value if task.skipped else Status.COMPLETED.value
                    break
                for row in rows:
                    if time.monotonic() - renewed_at >= 15:
                        renewed, new_version = store.compare_and_set('active', lease_version,
                            {'task_id': task.task_id}, ttl=cls.LEASE_TTL)
                        if not renewed:
                            task.status, task.message = Status.PARTIAL.value, '检索租约已失效，请重新检索'
                            break
                        lease_version = new_version
                        renewed_at = time.monotonic()
                    if time.monotonic() - checked_at >= 0.5:
                        checked_at = time.monotonic()
                        signals = store.get_many(['active', f'cancel:{task.task_id}'])
                        if signals.get('active') != {'task_id': task.task_id}:
                            task.status, task.message = Status.PARTIAL.value, '检索租约已失效，请重新检索'
                            break
                        if signals.get(f'cancel:{task.task_id}'):
                            task.status = Status.CANCELLED.value
                            break
                    task.scanned += 1
                    cursor = (row.create_time, row.id)
                    payload = None
                    hit = None
                    try:
                        payload, size, incomplete = cls.payload(task, row)
                        if size > cls.MAX_FILE_BYTES:
                            task.skipped += 1
                        else:
                            match, truncated = cls.match(payload, task.query.keyword)
                            task.skipped += int(incomplete or truncated)
                            if match:
                                hit = cls.hit(task, row, match)
                    except Exception:
                        # 过期、损坏和存储失败只计入覆盖缺口，不把内部地址或原文写日志。
                        task.skipped += 1
                        log.system.warning('event=content_search_record_unavailable record_id=%s', row.id)
                    finally:
                        # JSON只存活于当前记录；命中仅保留短片段，不携带原始请求/响应。
                        payload = None
                    if hit:
                        task.items.append(hit)
                        task.match_count += 1
                        if len(task.items) == cls.PAGE_SIZE:
                            cls.save_page(task)
                            task.items.clear()
                    if time.monotonic() - saved_at >= 2:
                        cls.save_page(task)
                        cls.save(task)
                        saved_at = time.monotonic()
                cls.save_page(task)
                cls.save(task)
                rows.clear()
                if task.status != Status.RUNNING.value:
                    break
            if task.skipped and not task.message:
                task.message = '部分记录已清理、截断、超限或不可读；未命中不代表未由平台产生'
            cls.save(task)
        except Exception:
            task.status, task.message, task.items, task.match_count = Status.FAILED.value, '检索失败，请重试或联系管理员检查服务日志', [], 0
            cls.save(task)
            log.system.exception('event=content_search_failed task_id=%s', task.task_id)
        finally:
            try:
                store.delete_if_version('active', lease_version)
            finally:
                close_old_connections()
                cls._slot.release()
