# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-10-17 11:31
# @Author : 毛鹏

from rest_framework import serializers

from src.apps.auto_ui.api.serializers.ui_case import UiCaseSerializers
from src.apps.auto_ui.api.serializers.ui_page_steps import PageStepsSerializersC
from src.apps.auto_ui.models import PageSteps, UiCaseStepsDetailed
from src.apps.auto_ui.services.page_step_detail import PageStepDetailMutationService
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class UiCaseStepsDetailedSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UiCaseStepsDetailed
        fields = '__all__'

    def validate_case_data(self, value):
        page_step = getattr(self.instance, 'page_step', None)
        if page_step is None:
            page_step_id = self.initial_data.get('page_step')
            if page_step_id not in (None, ''):
                page_step = PageSteps.objects.filter(id=page_step_id).first()
        project_product_id = page_step.project_product_id if page_step else None
        for item in value or []:
            if (
                    isinstance(item, dict)
                    and item.get('type') == 1
                    and str(item.get('ope_key') or '').startswith('assert_sql_')
            ):
                PageStepDetailMutationService.validate_sql_assertion_datasource(
                    item.get('page_step_details_data'),
                    project_product_id=project_product_id,
                )
        return value


class UiCaseStepsDetailedSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    case = UiCaseSerializers(read_only=True)
    page_step = PageStepsSerializersC(read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = UiCaseStepsDetailed
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'case',
            'page_step',
            'page_step__project_product',
            'page_step__project_product__project',
            'page_step__page',
            'page_step__module',
            'update_user')
        return queryset
