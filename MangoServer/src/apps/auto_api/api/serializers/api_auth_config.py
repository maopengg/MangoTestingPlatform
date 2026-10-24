# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: API授权Token配置

from src.apps.auto_api.api.serializers.api_auth_config_mutation import ApiAuthConfigSerializers
from src.apps.auto_api.api.serializers.api_info import ApiInfoSerializersC
from src.apps.task_center.formatters import format_time_task
from src.apps.test_center.formatters.related import format_notice_group
from src.apps.test_center.formatters.related import format_project_product
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class ApiAuthConfigSerializersC(ApiAuthConfigSerializers):
    project_product = RelatedObjectField(formatter=format_project_product, read_only=True)
    api_info = ApiInfoSerializersC(read_only=True)
    time_task = RelatedObjectField(formatter=format_time_task, read_only=True)
    notice_group = RelatedObjectField(formatter=format_notice_group, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'project_product',
            'project_product__project',
            'api_info',
            'time_task',
            'notice_group',
            'update_user',
        )
