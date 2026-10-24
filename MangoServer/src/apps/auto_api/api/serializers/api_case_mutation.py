from rest_framework import serializers

from src.apps.auto_api.api.serializers.mixins import ProductModuleBindingSerializerMixin
from src.apps.auto_api.models import ApiCase
from src.apps.auto_api.schemas.case_schema import (
    ApiEnvironmentKeyValueItem,
    ApiParametrizeSuite,
    validate_int_list,
    validate_scenario_tag_list,
    validate_model_list,
    validate_data_source_operation_list,
)


class ApiCaseSerializers(ProductModuleBindingSerializerMixin, serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiCase
        fields = '__all__'

    def validate_parametrize(self, value):
        return validate_model_list(value, ApiParametrizeSuite, '参数化')

    def validate_front_custom(self, value):
        return validate_model_list(value, ApiEnvironmentKeyValueItem, '前置方法')

    def validate_front_sql(self, value):
        return validate_data_source_operation_list(value, '前置数据库操作', self._project_product_id())

    def validate_front_headers(self, value):
        return validate_int_list(value, '前置请求头')

    def validate_front_public(self, value):
        return validate_int_list(value, '用例选择全局变量')

    def validate_front_auth_config(self, value):
        return validate_int_list(value, '用例选择授权配置')

    def validate_scenario_tags(self, value):
        return validate_scenario_tag_list(value)

    def validate_posterior_sql(self, value):
        return validate_data_source_operation_list(value, '后置数据库操作', self._project_product_id())

    def _project_product_id(self):
        project_product = self.initial_data.get('project_product')
        if isinstance(project_product, dict):
            project_product = project_product.get('id')
        return project_product or getattr(self.instance, 'project_product_id', None)
