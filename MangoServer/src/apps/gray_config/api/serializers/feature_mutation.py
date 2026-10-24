from rest_framework import serializers

from src.apps.gray_config.api.serializers.mixins import ProductModuleBindingSerializerMixin
from src.apps.gray_config.enums import GrayConfigTypeEnum
from src.apps.gray_config.exceptions import (
    GRAY_TYPE_CONFIG_GRAY_UNSUPPORTED,
    GRAY_PROJECT_PRODUCT_MODULE_INVALID,
    GRAY_FILE_GRAY_REQUIRED,
    GRAY_SQL_DATABASE_GRAY_REQUIRED,
    GRAY_SQL_CONFIG_GRAY_INVALID,
    GRAY_CODE_CONFIG_GRAY_INVALID,
    GrayConfigError,
)
from src.apps.gray_config.models import (
    GrayFeature,
)
from src.apps.gray_config.services.feature import GrayFeatureService


class GrayFeatureSerializer(ProductModuleBindingSerializerMixin, serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = GrayFeature
        fields = '__all__'
        validators = []

    def validate(self, attrs):
        if "path_config" in attrs:
            attrs["path_config"] = self.normalize_path_config(attrs.get("path_config"))
        project_product = attrs.get("project_product", self.instance.project_product if self.instance else None)
        module = attrs.get("module", self.instance.module if self.instance else None)
        if project_product and module and module.project_product_id != project_product.id:
            raise GrayConfigError(GRAY_PROJECT_PRODUCT_MODULE_INVALID)
        config_type = attrs.get("config_type", self.instance.config_type if self.instance else None)
        if config_type not in GrayConfigTypeEnum.obj():
            raise GrayConfigError(GRAY_TYPE_CONFIG_GRAY_UNSUPPORTED)
        yaml_file = attrs.get("yaml_file", self.instance.yaml_file if self.instance else None)
        datasource_alias = attrs.get(
            "datasource_alias",
            self.instance.datasource_alias if self.instance else None,
        )
        database = attrs.get("database", self.instance.database if self.instance else None)
        enable_sql = attrs.get("enable_sql", self.instance.enable_sql if self.instance else None)
        disable_sql = attrs.get("disable_sql", self.instance.disable_sql if self.instance else None)
        enable_code = attrs.get("enable_code", self.instance.enable_code if self.instance else None)
        disable_code = attrs.get("disable_code", self.instance.disable_code if self.instance else None)
        if config_type == GrayConfigTypeEnum.YAML.value:
            if not yaml_file:
                raise GrayConfigError(GRAY_FILE_GRAY_REQUIRED)
        if config_type == GrayConfigTypeEnum.SQL.value:
            if not datasource_alias and not database:
                raise GrayConfigError(GRAY_SQL_DATABASE_GRAY_REQUIRED)
            if datasource_alias:
                from src.apps.data_factory.services.datasource import DataFactoryDatasourceResolver

                DataFactoryDatasourceResolver.require_sql_alias(
                    datasource_alias,
                    project_product.id if project_product else None,
                    'SQL灰度',
                )
            if not enable_sql or not disable_sql:
                raise GrayConfigError(GRAY_SQL_CONFIG_GRAY_INVALID)
        if config_type == GrayConfigTypeEnum.CODE.value and (not enable_code or not disable_code):
            raise GrayConfigError(GRAY_CODE_CONFIG_GRAY_INVALID)
        return attrs

    @staticmethod
    def normalize_path_config(value):
        return GrayFeatureService.normalize_path_config(value)
