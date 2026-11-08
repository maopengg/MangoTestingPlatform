from src.apps.monitoring.exceptions import MonitoringError, MONITORING_TASK_NOT_ACCESSIBLE
from src.apps.monitoring.models import MonitoringTask
from src.apps.monitoring.models import MonitoringReport
from src.apps.monitoring.constants import TASK_DIAGNOSTIC_MESSAGE
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from django.db.models import Q
from django.db.models.functions import Trim


class MonitoringTaskSelector:
    @staticmethod
    def missing_log_path():
        return MonitoringTask.objects.annotate(_trimmed_log_path=Trim('log_path')).filter(
            Q(log_path__isnull=True) | Q(_trimmed_log_path=''),
        ).order_by('id')

    @staticmethod
    def failure_reason(task):
        if task.stopped_at is None:
            return None
        return MonitoringReport.objects.filter(
            task_id=task.id, msg=TASK_DIAGNOSTIC_MESSAGE, create_time__gte=task.stopped_at,
        ).order_by('-id').values_list('send_text', flat=True).first()

    @staticmethod
    def visible(user):
        queryset = MonitoringTask.objects.all()
        if user is None:
            return queryset.none()
        if not (PermissionMenuService.is_effective_super_admin(user)
                or ProjectProductScopeService.can_view_all_project_data(user)):
            queryset = queryset.filter(project_product_id__in=ProjectProductScopeService.project_product_ids_for_user(user))
        return queryset

    @classmethod
    def get(cls, user, task_id, *, for_update=False):
        queryset = cls.visible(user)
        if for_update:
            queryset = queryset.select_for_update()
        task = queryset.filter(id=task_id).first()
        if task is None:
            raise MonitoringError(MONITORING_TASK_NOT_ACCESSIBLE)
        return task
