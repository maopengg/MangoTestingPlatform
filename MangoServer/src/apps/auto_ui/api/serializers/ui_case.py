# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-03-25 18:53
# @Author : 毛鹏
from rest_framework import serializers

from src.apps.auto_api.schemas.case_schema import validate_int_list, validate_scenario_tag_list
from src.apps.auto_ui.api.serializers.mixins import ProductModuleBindingSerializerMixin
from src.apps.auto_ui.models import UiCase
from src.apps.auto_ui.selectors.case_publication import UiCasePublicationSelector
from src.apps.auto_ui.schemas.case_schema import (
    UiCaseFrontCustomSchema,
    UiCaseFrontSqlSchema,
    UiCaseParametrizeSuite,
    UiCasePosteriorSqlSchema,
    validate_data_source_items,
    validate_model_list,
)
from src.apps.test_center.formatters.related import format_product_module
from src.apps.test_center.formatters.related import format_project_product
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.formatters import format_user, format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class UiCaseSerializers(ProductModuleBindingSerializerMixin, serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UiCase
        fields = '__all__'
        read_only_fields = ('publication_status',)

    def validate_scenario_tags(self, value):
        return validate_scenario_tag_list(value)

    def validate_front_custom(self, value):
        return validate_model_list(value, UiCaseFrontCustomSchema, '前置自定义')

    def validate_parametrize(self, value):
        return validate_model_list(value, UiCaseParametrizeSuite, '参数化')

    def validate_front_sql(self, value):
        return validate_data_source_items(
            value,
            UiCaseFrontSqlSchema,
            '前置数据库操作',
            self._project_product_id(),
        )

    def validate_front_public(self, value):
        return validate_int_list(value, '用例选择全局变量')

    def validate_front_auth_config(self, value):
        return validate_int_list(value, '用例选择授权配置')

    def validate_posterior_sql(self, value):
        return validate_data_source_items(
            value,
            UiCasePosteriorSqlSchema,
            '后置数据库操作',
            self._project_product_id(),
        )

    def _project_product_id(self):
        project_product = self.initial_data.get('project_product')
        if isinstance(project_product, dict):
            project_product = project_product.get('id')
        return project_product or getattr(self.instance, 'project_product_id', None)


class UiCaseSerializersC(serializers.ModelSerializer):
    publication_status = serializers.SerializerMethodField()
    is_product_owner = serializers.BooleanField(read_only=True, default=False)

    def get_publication_status(self, instance):
        return UiCasePublicationSelector.status(instance)

    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, read_only=True)
    module = RelatedObjectField(formatter=format_product_module, read_only=True)
    case_people = RelatedObjectField(formatter=format_user, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = UiCase
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = ProductModuleService.with_full_paths(queryset, 'module').select_related(
            'project_product',
            'project_product__project',
            'case_people',
            'update_user')
        return queryset
