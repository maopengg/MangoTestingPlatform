import uuid

from django.db import transaction

from src.apps.monitoring.selectors.task import MonitoringTaskSelector


class MonitoringLogPathService:
    @staticmethod
    def new_path():
        return f'monitoring/logs/{uuid.uuid4().hex}.log'

    @classmethod
    def ensure(cls, task):
        # Imported and historical rows may have no runtime path. Keep existing logs intact.
        if not str(task.log_path or '').strip():
            task.log_path = cls.new_path()
            task.save(update_fields=['log_path'])
            return True
        return False

    @classmethod
    def repair_missing(cls, task_ids=None, *, apply=False):
        queryset = MonitoringTaskSelector.missing_log_path()
        if task_ids is not None:
            queryset = queryset.filter(id__in=task_ids)
        missing = queryset.count()
        repaired = 0
        if apply:
            for task_id in queryset.values_list('id', flat=True).iterator(chunk_size=200):
                with transaction.atomic(using=queryset.db):
                    task = queryset.select_for_update().filter(id=task_id).first()
                    if task is not None and cls.ensure(task):
                        repaired += 1
        return {'missing': missing, 'repaired': repaired}
