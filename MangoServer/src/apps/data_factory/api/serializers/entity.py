# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂实体视图

from rest_framework import serializers

from src.apps.data_factory.api.serializers.datasource_alias import DataFactoryDatasourceAliasSerializerC
from src.apps.data_factory.models import DataFactoryEntity
from src.apps.test_center.formatters.related import format_product_module_compact
from src.apps.test_center.formatters.related import format_project_product
from src.apps.test_center.services.project.product_module import ProductModuleService
from src.apps.user.formatters import format_user_simple
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.common.validators.serializer_fields import RelatedObjectField


class DataFactoryEntitySerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, cache_representation=True, read_only=True)
    module = RelatedObjectField(formatter=format_product_module_compact, read_only=True)
    datasource_alias = DataFactoryDatasourceAliasSerializerC(read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)
    status_changed_by = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = DataFactoryEntity
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return TestCenterQuerySelector.with_project_product_display(ProductModuleService.with_full_paths(queryset, 'module').select_related(
            'project_product',
            'project_product__project',
            'datasource_alias',
            'datasource_alias__project_product',
            'update_user',
            'status_changed_by',
        ))
