# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-01-15 10:56
# @Author : 毛鹏
from rest_framework import serializers

from src.apps.auto_ui.api.serializers.ui_element_mutation import PageElementSerializers
from src.apps.auto_ui.models import PageStepsDetailed
from src.apps.auto_ui.schemas.step_healing import validate_condition_group
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class PageStepsDetailedSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PageStepsDetailed
        fields = '__all__'

    def validate_precondition(self, value):
        return validate_condition_group(value, '节点前置条件')

    def validate_postcondition(self, value):
        return validate_condition_group(value, '节点后置条件')


class PageStepsDetailedSerializersC(serializers.ModelSerializer):
    # page_step = PageStepsSerializers(read_only=True)
    ele_name = PageElementSerializers(read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PageStepsDetailed
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            # 'page_step',
            'ele_name',
            'update_user')
        return queryset


class UiDuplicatePageStepNodeSerializer(serializers.Serializer):
    page_step_id = serializers.IntegerField(min_value=1)
    source_detail_id = serializers.IntegerField(min_value=1)
    node_id = serializers.CharField(max_length=128)
    flow_data = serializers.JSONField()
