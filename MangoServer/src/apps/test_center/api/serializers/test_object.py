# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework import serializers

from src.apps.test_center.api.serializers.project_product import ProjectProductSerializersC
from src.apps.test_center.models import TestObject
from src.apps.test_center.services.test_target import TestTargetService
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class TestObjectSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    def validate(self, attrs):
        value = attrs.get('value', self.instance.value if self.instance else '')
        config = attrs.get('target_config', getattr(self.instance, 'target_config', {}) if self.instance else {})
        if not value or config:
            attrs['target_config'] = TestTargetService.validate(config)
        return attrs

    class Meta:
        model = TestObject
        fields = '__all__'


class TestObjectSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = TestObject
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'project_product__project',
            'update_user',
        ).prefetch_related('project_product__owners')
        return queryset
