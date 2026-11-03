# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: UI授权配置

from src.apps.auto_ui.api.serializers.ui_auth_config_mutation import UiAuthConfigSerializers
from src.apps.auto_ui.api.serializers.ui_page_steps import PageStepsSerializersC
from src.apps.task_center.formatters import format_time_task
from src.apps.test_center.formatters.related import format_notice_group
from src.apps.test_center.formatters.related import format_project_product
from src.apps.user.formatters import format_user_simple
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.common.validators.serializer_fields import RelatedObjectField


class UiAuthConfigSerializersC(UiAuthConfigSerializers):
    project_product = RelatedObjectField(formatter=format_project_product, cache_representation=True, read_only=True)
    page_step = PageStepsSerializersC(read_only=True)
    time_task = RelatedObjectField(formatter=format_time_task, read_only=True)
    notice_group = RelatedObjectField(formatter=format_notice_group, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    @staticmethod
    def setup_eager_loading(queryset):
        return TestCenterQuerySelector.with_project_product_display(queryset.select_related(
            'project_product',
            'project_product__project',
            'page_step',
            'page_step__page',
            'page_step__module',
            'time_task',
            'notice_group',
            'update_user',
        ))
