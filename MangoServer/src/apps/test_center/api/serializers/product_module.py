# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-10-12 18:14
# @Author : 毛鹏
from django.db import transaction
from rest_framework import serializers

from src.apps.test_center.api.serializers.project_product import ProjectProductSerializers
from src.apps.test_center.exceptions import (
    SYSTEM_MODULE_MODULE_NAME_REQUIRED,
    TestCenterError,
)
from src.apps.test_center.models import ProductModule, ProjectProduct
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class ProductModulePathSerializer(serializers.Serializer):
    project_product = serializers.PrimaryKeyRelatedField(
        queryset=ProjectProduct.objects.all()
    )
    level_1_name = serializers.CharField(max_length=64)
    level_2_name = serializers.CharField(max_length=64)
    level_3_name = serializers.CharField(max_length=64)
    sort = serializers.IntegerField(default=0, required=False)

    def validate(self, attrs):
        for field in ('level_1_name', 'level_2_name', 'level_3_name'):
            attrs[field] = attrs[field].strip()
        if not all(attrs[field] for field in ('level_1_name', 'level_2_name', 'level_3_name')):
            raise TestCenterError(SYSTEM_MODULE_MODULE_NAME_REQUIRED)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        return ProductModuleService.create_path(
            validated_data['project_product'].id,
            validated_data['level_1_name'],
            validated_data['level_2_name'],
            validated_data['level_3_name'],
            sort=validated_data.get('sort', 0),
            update_user_id=validated_data.get('update_user_id'),
        )


class ProductModuleSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    full_path = serializers.CharField(source='get_full_path', read_only=True)
    project_product = ProjectProductSerializers(read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)
    parent = serializers.SerializerMethodField()

    class Meta:
        model = ProductModule
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'parent',
            'parent__parent',
            'update_user')
        return queryset

    def get_parent(self, obj):
        if not obj.parent_id:
            return None
        return ProductModuleSerializersC(instance=obj.parent).data
