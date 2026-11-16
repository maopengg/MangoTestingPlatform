import hashlib
import json

from django.db import transaction
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.task_center.enums import (
    WorkbenchTodoEventTypeEnum, WorkbenchTodoSourceTypeEnum,
    WorkbenchTodoSeverityEnum, WorkbenchTodoStatusEnum,
)
from src.apps.task_center.models import WorkbenchTodo
from src.apps.task_center.schemas.workbench import ReportInfrastructureTodoDetails
from src.apps.test_center.selectors.infrastructure import ReportInfrastructureSelector
from src.apps.test_center.enums.reporting import ReportExecutionPhaseEnum
from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService


class ReportInfrastructureTodoService:
    @classmethod
    def sync(cls, suite_id):
        from src.apps.task_center.services.workbench.todo import WorkbenchTodoService
        suite = ReportInfrastructureSelector.report(suite_id)
        key = f'report-infrastructure:{suite.project_product_id}:{suite.test_env}:{suite.tasks_id or suite.id}'
        rows = list(ReportInfrastructureSelector.details(suite.id))
        scope_fingerprint = hashlib.sha256(json.dumps(sorted({
            (row.get('type'), row.get('case_id')) for row in rows
        }), separators=(',', ':')).encode()).hexdigest()
        blocked = [row for row in rows if not row['is_excluded'] and (
            row['status'] == TaskEnum.INFRASTRUCTURE_BLOCKED.value or
            row.get('infrastructure_phase') == ReportExecutionPhaseEnum.INFRASTRUCTURE_BLOCKED.value or
            TestSuiteInfrastructureService.is_blocked(row.get('summary_data')))]
        if not blocked:
            if (suite.status in (TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value, TaskEnum.STOPPED.value)
                    or not rows or any(row['is_excluded'] or row['status'] in (TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value) for row in rows)):
                return
            previous = WorkbenchTodo.objects.filter(event_key=key).first()
            if previous and (len(rows) < int((previous.details or {}).get('execution_item_count', 0))
                    or (previous.details or {}).get('scope_fingerprint', scope_fingerprint) != scope_fingerprint):
                return
            if previous:
                from src.apps.auto_api.selectors.resource_cleanup import ApiResourceCleanupSelector
                from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
                if (ApiResourceCleanupSelector.has_unfinished_for_report(previous.source_id)
                        or DataFactoryQuerySelector.has_unfinished_cleanup_for_details(
                            ReportInfrastructureSelector.detail_ids(previous.source_id), suite.project_product_id)):
                    return
            WorkbenchTodo.objects.filter(event_key=key, status=WorkbenchTodoStatusEnum.PENDING.value,
                source_id__lte=suite.id).update(
                status=WorkbenchTodoStatusEnum.HANDLED.value, handled_at=timezone.now(),
                handle_note='同范围执行已形成有效结果，平台受阻已恢复', update_time=timezone.now())
            return
        count = len(blocked)
        name = suite.tasks.name if suite.tasks_id else suite.execution_name or str(suite.id)
        with transaction.atomic():
            # 以产品锁串行聚合，避免多个 Worker 为同一故障并发通知。
            # 聚合仅锁已有产品，不创建新的锁表或运行态凭证。
            from src.apps.test_center.models import ProjectProduct
            ProjectProduct.objects.select_for_update().get(id=suite.project_product_id)
            existing = WorkbenchTodo.objects.filter(event_key=key).first()
            details = dict(existing.details or {}) if existing else {}
            changed_report = details.get('test_suite_id') != suite.id
            episode = hashlib.sha256(f'{key}:{suite.id}'.encode()).hexdigest()
            if (existing and existing.status == WorkbenchTodoStatusEnum.HANDLED.value
                    and details.get('difference_fingerprint') == episode):
                return
            occurrence = int(details.get('report_count', 0)) + int(changed_report)
            WorkbenchTodoService._upsert(key, {
                'source_type': WorkbenchTodoSourceTypeEnum.TEST_REPORT.value,
                'event_type': WorkbenchTodoEventTypeEnum.REPORT_INFRASTRUCTURE_BLOCKED.value,
                'source_id': suite.id, 'project_product': suite.project_product,
                'module': None, 'severity': WorkbenchTodoSeverityEnum.DANGER.value,
                'title': f'测试执行平台受阻：{name}'[:191],
                'summary': f'{count} 条执行记录受阻，结果不完整。请联系平台开发者处理，修复后重新执行验证。',
                'occurred_at': existing.occurred_at if existing and existing.status == WorkbenchTodoStatusEnum.PENDING.value else timezone.now(),
                'details': ReportInfrastructureTodoDetails.model_validate({'version': 1, 'test_suite_id': suite.id, 'task_id': suite.tasks_id,
                    'test_env': suite.test_env, 'blocked_count': count,
                    'execution_item_count': len(rows),
                    'scope_fingerprint': scope_fingerprint,
                    'owner_notified': details.get('owner_notified', False) if existing and existing.status == WorkbenchTodoStatusEnum.PENDING.value else False,
                    'report_count': occurrence, 'difference_fingerprint': episode,
                    'url': f'/report/system/details?id={suite.id}',
                    'fallback_owner_id': getattr(suite.tasks, 'case_people_id', None) if suite.tasks_id else suite.user_id,
                    'latest_occurred_at': timezone.now().isoformat()}).model_dump(mode='json'),
            }, notify_owner=False)
            notify = existing is None or existing.status != WorkbenchTodoStatusEnum.PENDING.value or not details.get('owner_notified')
            if notify:
                transaction.on_commit(lambda: cls.notify(key))

    @staticmethod
    def notify(key):
        from src.apps.task_center.services.workbench.todo import WorkbenchTodoService
        with transaction.atomic():
            todo = WorkbenchTodo.objects.select_for_update().select_related('project_product__project').get(event_key=key)
            if todo.status != WorkbenchTodoStatusEnum.PENDING.value or (todo.details or {}).get('owner_notified'):
                return
            if WorkbenchTodoService._notify_owner(todo):
                todo.details = {**todo.details, 'owner_notified': True}
                todo.save(update_fields=['details', 'update_time'])

    @classmethod
    def reconcile(cls):
        ids = set(ReportInfrastructureSelector.blocked_report_ids())
        ids.update(WorkbenchTodo.objects.filter(
            event_type=WorkbenchTodoEventTypeEnum.REPORT_INFRASTRUCTURE_BLOCKED.value,
            status=WorkbenchTodoStatusEnum.PENDING.value).values_list('source_id', flat=True))
        for suite_id in ids:
            cls.sync(suite_id)
        return {'report_infrastructure_scanned': len(ids)}
