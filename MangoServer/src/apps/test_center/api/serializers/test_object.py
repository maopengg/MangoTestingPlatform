# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework import serializers

from src.apps.test_center.selectors.querysets import TestCenterQuerySelector

from src.apps.test_center.api.serializers.project_product import ProjectProductSerializersC
from src.apps.test_center.models import TestObject
from src.apps.test_center.services.test_target import TestTargetService
from src.apps.test_center.services.test_object_probe import TestObjectProbeService
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class TestObjectProbeSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    address = serializers.CharField(max_length=1024, required=False, allow_blank=True, default='')


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
    network_test_addresses = serializers.SerializerMethodField()
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = TestObject
        fields = '__all__'

    def get_network_test_addresses(self, obj):
        return TestObjectProbeService.network_options(obj)

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'project_product__project',
            'update_user',
        ).prefetch_related('project_product__owners')
        return TestCenterQuerySelector.with_project_product_display(queryset)
