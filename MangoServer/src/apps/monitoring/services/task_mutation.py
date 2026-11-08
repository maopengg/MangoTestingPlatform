from django.db import transaction

from src.apps.monitoring.enums import MonitoringTaskStatusEnum
from src.apps.monitoring.exceptions import (
    MonitoringError, MONITORING_PRODUCT_NOT_ACCESSIBLE, MONITORING_NOTICE_GROUP_INVALID,
    MONITORING_TASK_INPUT_INVALID, MONITORING_SCRIPT_CONTENT_REQUIRED,
)
from src.apps.monitoring.models import MonitoringTask
from src.apps.monitoring.selectors.task import MonitoringTaskSelector
from src.apps.monitoring.services.task_control import MonitoringTaskControlService
from src.apps.monitoring.services.log_path import MonitoringLogPathService
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.user.services.permission import ProjectProductScopeService


class MonitoringTaskMutationService:
    @staticmethod
    def validate_notice(product_id, values):
        group_id = values.get('notice_group_id')
        if values.get('is_notice') and not group_id:
            raise MonitoringError(MONITORING_NOTICE_GROUP_INVALID)
        if group_id:
            project_id = TestCenterQuerySelector.project_product().filter(id=product_id).values_list('project_id', flat=True).first()
            if not TestCenterQuerySelector.notice_group().filter(id=group_id, project_id=project_id).exists():
                raise MonitoringError(MONITORING_NOTICE_GROUP_INVALID)

    @staticmethod
    def create_validated(values):
        values = dict(values)
        if not values.get('script_content'):
            raise MonitoringError(MONITORING_SCRIPT_CONTENT_REQUIRED)
        values.update(log_path=MonitoringLogPathService.new_path(), status=MonitoringTaskStatusEnum.QUEUED.value)
        return MonitoringTask.objects.create(**values)

    @classmethod
    def create(cls, user, product_id, fields):
        if user is None or not ProjectProductScopeService.has_project_product(user, product_id):
            raise MonitoringError(MONITORING_PRODUCT_NOT_ACCESSIBLE)
        if not TestCenterQuerySelector.project_product().filter(id=product_id).exists():
            raise MonitoringError(MONITORING_PRODUCT_NOT_ACCESSIBLE)
        values = fields.model_dump()
        cls.validate_notice(product_id, values)
        return cls.create_validated({**values, 'project_product_id': product_id, 'update_user_id': user.id})

    @classmethod
    @transaction.atomic
    def update(cls, user, task_id, fields):
        task = MonitoringTaskSelector.get(user, task_id, for_update=True)
        values = fields.model_dump(exclude_unset=True)
        if not values or any(values.get(key, '') is None for key in ('name', 'script_content', 'is_notice')):
            raise MonitoringError(MONITORING_TASK_INPUT_INVALID)
        cls.validate_notice(task.project_product_id, {
            'is_notice': values.get('is_notice', task.is_notice),
            'notice_group_id': values.get('notice_group_id', task.notice_group_id),
        })
        for key, value in values.items():
            setattr(task, key, value)
        task.update_user_id = user.id
        task.save(update_fields=[*values, 'update_user', 'update_time'])
        return task

    @classmethod
    def start(cls, user, task_id):
        return MonitoringTaskControlService.request_start(MonitoringTaskSelector.get(user, task_id))

    @classmethod
    @transaction.atomic
    def stop(cls, user, task_id):
        task = MonitoringTaskSelector.get(user, task_id, for_update=True)
        task.status = MonitoringTaskStatusEnum.STOPPED.value
        task.save(update_fields=['status', 'update_time'])
        return task
