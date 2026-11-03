from django.core.exceptions import ObjectDoesNotExist
# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏
from rest_framework import serializers

from src.apps.task_center.api.serializers.time_tasks import TimeTasksSerializers
from src.apps.task_center.exceptions import (
    SYSTEM_TASK_GROUP_TASK_CONFIG_GENERATE_NOT_ALLOWED,
    TaskCenterError,
)
from src.apps.task_center.models import Tasks
from src.apps.task_center.services.selection.save_validation import ScheduledTaskSaveValidationService
from src.apps.test_center.formatters.related import format_notice_group
from src.apps.test_center.formatters.related import format_product_module
from src.apps.test_center.formatters.related import format_project_product
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.formatters import format_user, format_user_simple
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.common.validators.serializer_fields import RelatedObjectField


class TasksSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = Tasks
        fields = '__all__'
        read_only_fields = ('diagnostic_file_path', 'task_group', 'task_group_revision')

    def to_internal_value(self, data):
        return super().to_internal_value(ScheduledTaskSaveValidationService.normalize_input(data))

    def validate(self, attrs):
        if self.instance is not None and self.instance.task_group_id:
            if 'report_retention_policy' in attrs and set(attrs) <= {'report_retention_policy', 'update_user'}:
                return attrs
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_GENERATE_NOT_ALLOWED)
        return ScheduledTaskSaveValidationService.validate(
            super().validate(attrs),
            instance=self.instance,
        )


class TasksSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, cache_representation=True, read_only=True)
    module = RelatedObjectField(formatter=format_product_module, read_only=True)
    timing_strategies = TimeTasksSerializers(many=True, read_only=True)
    case_people = RelatedObjectField(formatter=format_user, read_only=True)
    notice_group = RelatedObjectField(formatter=format_notice_group, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)
    task_group_name = serializers.CharField(source='task_group.name', read_only=True)
    task_group_member_id = serializers.SerializerMethodField()

    class Meta:
        model = Tasks
        fields = '__all__'
        read_only_fields = ('diagnostic_file_path', 'task_group', 'task_group_revision')

    @staticmethod
    def get_task_group_member_id(instance):
        if not instance.task_group_id:
            return None
        try:
            return instance.task_group_member.id
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = ProductModuleService.with_full_paths(queryset, 'module').select_related(
            'project_product',
            'project_product__project',
            'notice_group',
            'case_people',
            'update_user',
            'task_group',
            'task_group_member',
        ).prefetch_related('timing_strategies')
        return TestCenterQuerySelector.with_project_product_display(queryset)
