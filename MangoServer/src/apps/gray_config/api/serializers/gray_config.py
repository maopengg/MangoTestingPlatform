# -*- coding: utf-8 -*-
from rest_framework import serializers

from src.apps.data_factory.formatters import format_datasource_alias
from src.apps.gray_config.exceptions import (
    GRAY_CONFIG_MINIMUM_REQUIRED,
    GRAY_REPOSITORY_CONFIG_GRAY_DUPLICATED,
    GRAY_PROJECT_PRODUCT_FILE_CONFIG_DUPLICATED,
    GRAY_FILE_REPOSITORY_CONFIG_BINDING_GRAY_DUPLICATED,
    GrayConfigError,
)
from src.apps.gray_config.models import (
    AutomationCaseGrayConfig,
    GrayExecutionLog,
    GrayFeature,
    GrayRepository,
    GrayYamlFile,
    GrayYamlFileBinding,
)
from src.apps.gray_config.services.repository_path import GrayRepositoryPathService
from src.apps.test_center.formatters.related import format_data_source
from src.apps.test_center.formatters.related import format_product_module_compact
from src.apps.test_center.formatters.related import format_project_product
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class GrayRepositorySerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = GrayRepository
        fields = '__all__'
        extra_kwargs = {"access_token": {"write_only": True, "required": False}}
        validators = []

    def validate(self, attrs):
        if "config_dirs" in attrs:
            attrs["config_dirs"] = GrayRepositoryPathService.normalize_dirs(attrs.get("config_dirs"))
        config_dirs = attrs.get("config_dirs", self.instance.config_dirs if self.instance else [])
        if not config_dirs:
            raise GrayConfigError(GRAY_CONFIG_MINIMUM_REQUIRED)
        name = attrs.get("name", self.instance.name if self.instance else None)
        test_env = attrs.get("test_env", self.instance.test_env if self.instance else None)
        if name and GrayRepository.objects.exclude(id=getattr(self.instance, "id", None)).filter(
                name=name,
                test_env=test_env,
        ).exists():
            raise GrayConfigError(GRAY_REPOSITORY_CONFIG_GRAY_DUPLICATED)
        if self.instance and attrs.get("access_token") in ("", None):
            attrs.pop("access_token", None)
        return attrs


class GrayRepositorySerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    last_update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)
    access_token = serializers.SerializerMethodField()

    class Meta:
        model = GrayRepository
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("last_update_user")

    @staticmethod
    def get_access_token(obj):
        return "已配置" if obj.access_token else "未配置"


class GrayYamlFileSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = GrayYamlFile
        fields = '__all__'
        validators = []

    def validate(self, attrs):
        project_product = attrs.get("project_product", self.instance.project_product if self.instance else None)
        name = attrs.get("name", self.instance.name if self.instance else None)
        if project_product and name and GrayYamlFile.objects.exclude(
                id=getattr(self.instance, "id", None)
        ).filter(project_product=project_product, name=name).exists():
            raise GrayConfigError(GRAY_PROJECT_PRODUCT_FILE_CONFIG_DUPLICATED)
        return attrs


class GrayYamlFileBindingSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = GrayYamlFileBinding
        fields = '__all__'
        validators = []

    def validate(self, attrs):
        yaml_file = attrs.get("yaml_file", self.instance.yaml_file if self.instance else None)
        repository = attrs.get("repository", self.instance.repository if self.instance else None)
        file_path = attrs.get("file_path", self.instance.file_path if self.instance else None)
        if repository and file_path:
            attrs["file_path"] = GrayRepositoryPathService.ensure_file_allowed(repository, file_path)
        if yaml_file and repository and GrayYamlFileBinding.objects.exclude(
                id=getattr(self.instance, "id", None)
        ).filter(yaml_file=yaml_file, repository=repository).exists():
            raise GrayConfigError(GRAY_FILE_REPOSITORY_CONFIG_BINDING_GRAY_DUPLICATED)
        return attrs


class GrayYamlFileBindingSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    yaml_file = serializers.PrimaryKeyRelatedField(read_only=True)
    repository = GrayRepositorySerializerC(read_only=True)
    last_update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = GrayYamlFileBinding
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("repository", "last_update_user")


class GrayYamlFileSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, read_only=True)
    last_update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)
    bindings = GrayYamlFileBindingSerializerC(source="grayyamlfilebinding_set", many=True, read_only=True)

    class Meta:
        model = GrayYamlFile
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            "project_product",
            "project_product__project",
            "last_update_user",
        ).prefetch_related("grayyamlfilebinding_set", "grayyamlfilebinding_set__repository")


class GrayFeatureSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, read_only=True)
    module = RelatedObjectField(formatter=format_product_module_compact, read_only=True)
    yaml_file = GrayYamlFileSerializerC(read_only=True)
    database = RelatedObjectField(formatter=format_data_source, read_only=True)
    datasource_alias = RelatedObjectField(formatter=format_datasource_alias, read_only=True)
    last_update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = GrayFeature
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return ProductModuleService.with_full_paths(queryset, 'module').select_related(
            "project_product",
            "project_product__project",
            "yaml_file",
            "database",
            "datasource_alias",
            "last_update_user",
        )


class AutomationCaseGrayConfigSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = AutomationCaseGrayConfig
        fields = '__all__'
        validators = []


class AutomationCaseGrayConfigSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    gray_feature = GrayFeatureSerializerC(read_only=True)
    last_update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = AutomationCaseGrayConfig
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return ProductModuleService.with_full_paths(
            queryset,
            'gray_feature__module',
        ).select_related(
            "gray_feature",
            "gray_feature__project_product",
            "gray_feature__yaml_file",
            "gray_feature__database",
            "last_update_user",
        )


class GrayExecutionLogSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    gray_feature = GrayFeatureSerializerC(read_only=True)
    repository = GrayRepositorySerializerC(read_only=True)
    yaml_file = GrayYamlFileSerializerC(read_only=True)
    yaml_file_binding = GrayYamlFileBindingSerializerC(read_only=True)
    database = RelatedObjectField(formatter=format_data_source, read_only=True)

    class Meta:
        model = GrayExecutionLog
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            "gray_feature",
            "repository",
            "yaml_file",
            "yaml_file_binding",
            "yaml_file_binding__repository",
            "database",
        )
