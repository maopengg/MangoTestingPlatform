from rest_framework import serializers
from rest_framework.request import Request

from src.apps.auto_api.formatters import format_api_case
from src.apps.auto_pytest.formatters import format_pytest_case
from src.apps.auto_ui.formatters import format_ui_case
from src.apps.task_center.api.serializers.tasks import TasksSerializers
from src.apps.task_center.enums.execution import AutomationExecutionScopeEnum
from src.apps.task_center.exceptions import (
    SYSTEM_TASK_CATEGORY_CASE_EXECUTION_DELETE_NOT_ALLOWED,
    TaskCenterError,
)
from src.apps.task_center.models import TasksDetails
from src.common.responses.response_msg import (
    RESPONSE_MSG_0262,
    RESPONSE_MSG_0263,
    RESPONSE_MSG_0264,
    RESPONSE_MSG_0277,
    RESPONSE_MSG_0279,
)
from src.common.validators.serializer_fields import RelatedObjectField


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏


def get_request_user_id(request: Request) -> int | None:
    user = getattr(request, 'user', None)
    if isinstance(user, dict):
        return user.get('id')
    user_obj = getattr(user, 'user_obj', None)
    return getattr(user_obj or user, 'id', None)


def task_case_binding_error(result):
    if result.unpublished_ids:
        return RESPONSE_MSG_0279
    if result.type_mismatched_ids:
        return RESPONSE_MSG_0277
    if result.product_mismatched_ids:
        return RESPONSE_MSG_0262
    if result.module_mismatched_ids:
        return RESPONSE_MSG_0263
    if result.missing_ids:
        return RESPONSE_MSG_0264
    return None


class TasksDetailsSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = TasksDetails
        fields = '__all__'

    def validate(self, attrs):
        attrs = super().validate(attrs)
        task = attrs.get('task', getattr(self.instance, 'task', None))
        if task and task.execution_scope != AutomationExecutionScopeEnum.MANUAL.value:
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_CASE_EXECUTION_DELETE_NOT_ALLOWED)
        return attrs


class TasksDetailsSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    task = TasksSerializers(read_only=True)
    ui_case = RelatedObjectField(formatter=format_ui_case, read_only=True)
    api_case = RelatedObjectField(formatter=format_api_case, read_only=True)
    pytest_case = RelatedObjectField(formatter=format_pytest_case, read_only=True)
    api_case_version_label = serializers.CharField(
        source='api_case_release.version_label',
        read_only=True,
        allow_null=True,
    )
    api_case_revision_no = serializers.IntegerField(
        source='api_case_revision.revision_no',
        read_only=True,
        allow_null=True,
    )
    update_user_name = serializers.CharField(source='update_user.name', read_only=True, allow_null=True)

    class Meta:
        model = TasksDetails
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'task',
            'ui_case',
            'api_case',
            'api_case_revision',
            'api_case_release',
            'update_user',
            'pytest_case'
        )
        return queryset
