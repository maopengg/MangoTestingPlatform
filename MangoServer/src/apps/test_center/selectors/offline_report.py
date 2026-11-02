from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.task_center.selectors.querysets import ScheduleFireQuerySelector
from src.apps.test_center.enums.report_delivery import ReportSourceEnum
from src.apps.test_center.exceptions import REPORT_ARTIFACT_INVALID, TestCenterError
from src.apps.test_center.models import TestSuite
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService


class OfflineReportSelector:
    @classmethod
    def options(cls, user, source_kind, source_id, page=1, page_size=20):
        cls.require_permission(user)
        if source_kind == ReportSourceEnum.SUITE:
            queryset = TestSuite.objects.filter(tasks_id=source_id, report_retained=True)
            fields = ('id', 'execution_name', 'test_env', 'create_time', 'status')
            ordering = ('-create_time', '-id')
        else:
            queryset = ScheduleFireQuerySelector.scheduled_task_group_execution().filter(
                task_group_id=source_id, finished_at__isnull=False)
            fields = ('id', 'task_group_name', 'test_env', 'planned_at', 'status')
            ordering = ('-planned_at', '-id')
        if not (PermissionMenuService.is_effective_super_admin(user)
                or ProjectProductScopeService.can_view_all_project_data(user)):
            queryset = queryset.filter(project_product_id__in=ProjectProductScopeService.project_product_ids_for_user(user))
        queryset = queryset.exclude(status__in=(TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value))
        count = queryset.count()
        offset = (page - 1) * page_size
        items = []
        for row in queryset.order_by(*ordering).values(*fields)[offset:offset + page_size]:
            started_at = row.get('create_time') or row.get('planned_at')
            if timezone.is_aware(started_at):
                started_at = timezone.localtime(started_at)
            items.append({
                'id': row['id'], 'name': row.get('execution_name') or row.get('task_group_name') or '',
                'test_env': row['test_env'], 'status': row['status'],
                'started_at': started_at.strftime('%Y-%m-%d %H:%M:%S'),
            })
        return {'items': items, 'count': count, 'page': page, 'page_size': page_size}

    @staticmethod
    def require_permission(user, permission='report:read'):
        if user is None or (not PermissionMenuService.is_effective_super_admin(user) and permission not in PermissionMenuService.permission_keys_for_user(user)):
            raise TestCenterError(REPORT_ARTIFACT_INVALID)

    @classmethod
    def require_product(cls, user, product_id):
        cls.require_permission(user)
        if not ProjectProductScopeService.has_project_product(user, product_id):
            raise TestCenterError(REPORT_ARTIFACT_INVALID)
