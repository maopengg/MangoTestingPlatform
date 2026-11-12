# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2025-02-18 20:15
# @Author : 毛鹏
from rest_framework import serializers

from src.apps.auto_pytest.api.serializers.mixins import ProductModuleBindingSerializerMixin
from src.apps.auto_pytest.api.serializers.pytest_repository import PytestRepositorySerializer
from src.apps.auto_pytest.models import PytestProduct
from src.apps.auto_pytest.services.repository.repository_service import RepositoryGitService
from src.apps.auto_pytest.services.synchronization.product_sync import PytestProductSyncService
from src.apps.test_center.formatters.related import format_project_product
from src.apps.user.formatters import format_user_simple
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.common.validators.serializer_fields import RelatedObjectField


class PytestProductSerializers(ProductModuleBindingSerializerMixin, serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PytestProduct
        fields = '__all__'
        read_only_fields = ('file_name', 'init_file')

    @staticmethod
    def validate_working_directory(value):
        if not value:
            return None
        return PytestProductSyncService._normalize_directory(value, allow_root=True)

    @staticmethod
    def validate_pytest_config_path(value):
        return RepositoryGitService.repo_file_path(value) if value else None

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if (
                self.instance is not None
                and 'repository' in attrs
                and attrs['repository'] != self.instance.repository
        ):
            raise serializers.ValidationError({
                'repository': '已导入的 Pytest 项目不能直接切换仓库，请重新导入项目',
            })
        return attrs


class PytestProductSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, cache_representation=True, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)
    repository = PytestRepositorySerializer(read_only=True)
    case_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = PytestProduct
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'project_product__project',
            'update_user',
            'repository',
        )
        return TestCenterQuerySelector.with_project_product_display(queryset)
