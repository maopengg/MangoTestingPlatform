# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-01-15 22:06
# @Author : 毛鹏
from rest_framework import serializers

from src.apps.auto_ui.api.serializers.mixins import ProductModuleBindingSerializerMixin
from src.apps.auto_ui.api.serializers.ui_page_mutation import PageSerializers
from src.apps.auto_ui.models import PageSteps
from src.apps.auto_ui.schemas.case_schema import validate_flow_data
from src.apps.auto_ui.schemas.step_healing import validate_condition_group, validate_healing_policy
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.formatters.related import format_product_module
from src.apps.test_center.formatters.related import format_project_product
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class PageStepsSerializers(ProductModuleBindingSerializerMixin, serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PageSteps
        fields = '__all__'
        extra_kwargs = {'config_version': {'read_only': True}}

    def validate_flow_data(self, value):
        normalized = validate_flow_data(value)
        if not self.instance:
            return normalized

        existing_nodes = (getattr(self.instance, 'flow_data', None) or {}).get('nodes', [])
        existing_config_ids = {
            str(node.get('id')): (node.get('config') or {}).get('id')
            for node in existing_nodes
            if isinstance(node, dict) and node.get('id') is not None
        }
        for node in normalized.get('nodes', []):
            if not isinstance(node, dict) or node.get('id') is None:
                continue
            config = node.setdefault('config', {})
            if config.get('id') is None:
                existing_id = existing_config_ids.get(str(node['id']))
                if existing_id is not None:
                    config['id'] = existing_id
        return normalized

    def validate_entry_criteria(self, value):
        return validate_condition_group(value, '进入条件')

    def validate_success_criteria(self, value):
        return validate_condition_group(value, '成功条件')

    def validate_healing_policy(self, value):
        return validate_healing_policy(value)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        enabled = attrs.get(
            'healing_enabled', getattr(self.instance, 'healing_enabled', False),
        )
        if enabled:
            goal = attrs.get('goal', getattr(self.instance, 'goal', None))
            success = attrs.get(
                'success_criteria', getattr(self.instance, 'success_criteria', {}),
            )
            policy = attrs.get(
                'healing_policy', getattr(self.instance, 'healing_policy', {}),
            )
            if not str(goal or '').strip():
                raise serializers.ValidationError({'goal': '启用流程自愈后必须填写流程目标'})
            if not (success or {}).get('conditions'):
                raise serializers.ValidationError({'success_criteria': '启用流程自愈后必须配置成功条件'})
            if (policy or {}).get('mode') not in {'suggest_only', 'execute_low_risk'}:
                raise serializers.ValidationError({'healing_policy': '启用流程自愈后必须选择运行模式'})
        return attrs

    def update(self, instance, validated_data):
        tracked = {
            'name', 'goal', 'entry_criteria', 'success_criteria', 'healing_enabled',
            'healing_policy', 'flow_data',
        }
        changed = any(
            field in validated_data and validated_data[field] != getattr(instance, field)
            for field in tracked
        )
        if changed:
            validated_data['config_version'] = instance.config_version + 1
        return super().update(instance, validated_data)


class UiPageStepHealRecordQuerySerializer(serializers.Serializer):
    page_step_id = serializers.IntegerField(min_value=1)
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)


class UiPageStepHealReviewSerializer(serializers.Serializer):
    record_id = serializers.IntegerField(min_value=1)
    reviewed_flow_data = serializers.JSONField(required=False)


class UiPageStepVersionQuerySerializer(serializers.Serializer):
    page_step_id = serializers.IntegerField(min_value=1)


class UiPageStepRollbackSerializer(serializers.Serializer):
    page_step_id = serializers.IntegerField(min_value=1)
    version = serializers.IntegerField(min_value=1)


class PageStepsSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, read_only=True)
    page = PageSerializers(read_only=True)
    module = RelatedObjectField(formatter=format_product_module, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = PageSteps
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = ProductModuleService.with_full_paths(queryset, 'module').select_related(
            'project_product',
            'project_product__project',
            'page',
            'update_user')
        return queryset


class UiStepDebugControlSerializer(serializers.Serializer):
    page_step_detail_id = serializers.IntegerField(required=False, min_value=1)
    close_after_execution = serializers.BooleanField(default=False)
    before_wait_seconds = serializers.IntegerField(default=1, min_value=0, max_value=3600)
    after_wait_seconds = serializers.IntegerField(default=1, min_value=0, max_value=3600)
    close_live_after_execution = serializers.BooleanField(default=False)


class UiOpenStepBrowserSerializer(serializers.Serializer):
    page_step_id = serializers.IntegerField(min_value=1)
    test_env = serializers.ChoiceField(choices=EnvironmentEnum.get_key_list())


class UiPageStepReferencedCasesSerializer(serializers.Serializer):
    page_step_id = serializers.IntegerField(min_value=1)


class UiPageStepRecordingCommitSerializer(serializers.Serializer):
    page_id = serializers.IntegerField(min_value=1)
    name = serializers.CharField(max_length=64)
    nodes = serializers.ListField(child=serializers.DictField(), min_length=1, max_length=500)
