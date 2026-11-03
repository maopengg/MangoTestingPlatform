from django.db import transaction
from pydantic import ValidationError
from rest_framework import serializers

from src.apps.data_factory.api.serializers.entity import DataFactoryEntitySerializerC
from src.apps.data_factory.api.serializers.mixins import ProductModuleBindingSerializerMixin
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_SCENARIO_MODULE_TEMPLATE_BINDING_INVALID,
    DATA_FACTORY_PROJECT_PRODUCT_MODULE_INVALID,
    DATA_FACTORY_PROJECT_PRODUCT_ENTITY_INVALID,
    DATA_FACTORY_MODULE_ENTITY_INVALID,
    DATA_FACTORY_ENTITY_NAME_TEMPLATE_DUPLICATED,
    DATA_FACTORY_FIELD_INVALID,
    DATA_FACTORY_CONFIG_INVALID,
    DataFactoryError,
)
from src.apps.data_factory.models import DataFactoryTemplate, DataFactoryTemplateItem
from src.apps.data_factory.schemas.configuration import (
    DataFactoryFieldOverrideRules,
    DataFactoryOutputConfig,
    DataFactoryPostInsertUpdates,
)
from src.apps.test_center.formatters.related import format_product_module_compact
from src.apps.test_center.formatters.related import format_project_product
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.formatters import format_user_simple
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.common.validators.serializer_fields import RelatedObjectField


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂模板视图


class DataFactoryTemplateItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    def to_internal_value(self, data):
        data = dict(data or {})
        data.pop('cleanup_strategy', None)
        data.pop('enabled', None)
        return super().to_internal_value(data)

    class Meta:
        model = DataFactoryTemplateItem
        fields = '__all__'
        extra_kwargs = {
            'template': {'required': False},
        }

    def validate(self, attrs):
        template = attrs.get('template', self.instance.template if self.instance else None)
        child_template = attrs.get('child_template', self.instance.child_template if self.instance else None)
        if template and child_template and template.id == child_template.id:
            raise serializers.ValidationError("场景模板不能关联自身")
        if template and child_template and template.project_product_id != child_template.project_product_id:
            raise serializers.ValidationError("关联模板必须属于同一个项目/产品")
        field_overrides = attrs.get('field_overrides', self.instance.field_overrides if self.instance else {})
        try:
            attrs['field_overrides'] = DataFactoryFieldOverrideRules.model_validate(field_overrides or {}).model_dump()
        except ValidationError as error:
            raise serializers.ValidationError(f"关联模板字段覆盖规则格式错误：{error}") from error
        return attrs


class DataFactoryTemplateItemSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    child_template_detail = serializers.SerializerMethodField()
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = DataFactoryTemplateItem
        fields = '__all__'

    @staticmethod
    def get_child_template_detail(obj):
        if not obj.child_template_id:
            return None
        template = obj.child_template
        return {
            "id": template.id,
            "name": template.name,
            "entity": {
                "id": template.entity_id,
                "name": template.entity.name if template.entity_id else None,
                "table_name": template.entity.table_name if template.entity_id else None,
            },
            "field_overrides": template.field_overrides,
            "output_config": template.output_config,
            "cleanup_strategy": template.cleanup_strategy,
            "usage_scope": template.usage_scope,
            "status": template.status,
        }


class DataFactoryTemplateSerializer(ProductModuleBindingSerializerMixin, serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    items = DataFactoryTemplateItemSerializer(many=True, required=False)

    class Meta:
        model = DataFactoryTemplate
        fields = '__all__'
        validators = []
        read_only_fields = ('config_status',)

    def validate(self, attrs):
        project_product = attrs.get('project_product', self.instance.project_product if self.instance else None)
        module = attrs.get('module', self.instance.module if self.instance else None)
        entity = attrs.get('entity', self.instance.entity if self.instance else None)
        name = attrs.get('name', self.instance.name if self.instance else None)
        if not module:
            raise DataFactoryError(DATA_FACTORY_SCENARIO_MODULE_TEMPLATE_BINDING_INVALID)
        if project_product and module and module.project_product_id != project_product.id:
            raise DataFactoryError(DATA_FACTORY_PROJECT_PRODUCT_MODULE_INVALID)
        if project_product and entity and entity.project_product_id != project_product.id:
            raise DataFactoryError(DATA_FACTORY_PROJECT_PRODUCT_ENTITY_INVALID)
        if module and entity and entity.module_id and entity.module_id != module.id:
            raise DataFactoryError(DATA_FACTORY_MODULE_ENTITY_INVALID)
        if entity and name:
            queryset = DataFactoryTemplate.objects.filter(entity=entity, name=name)
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            if queryset.exists():
                raise DataFactoryError(DATA_FACTORY_ENTITY_NAME_TEMPLATE_DUPLICATED, value=(name,))
        field_overrides = attrs.get('field_overrides', self.instance.field_overrides if self.instance else {})
        try:
            attrs['field_overrides'] = DataFactoryFieldOverrideRules.model_validate(field_overrides or {}).model_dump()
        except ValidationError as error:
            raise DataFactoryError(DATA_FACTORY_FIELD_INVALID, value=(error,)) from error
        output_config = attrs.get('output_config', self.instance.output_config if self.instance else [])
        try:
            attrs['output_config'] = DataFactoryOutputConfig.model_validate(output_config or []).model_dump()
        except ValidationError as error:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(error,)) from error
        post_insert_updates = attrs.get(
            'post_insert_updates',
            self.instance.post_insert_updates if self.instance else [],
        )
        try:
            attrs['post_insert_updates'] = DataFactoryPostInsertUpdates.model_validate(
                post_insert_updates or []
            ).model_dump()
        except ValidationError as error:
            raise serializers.ValidationError(f"插入后回写配置格式错误：{error}") from error
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop('items', [])
        instance = super().create(validated_data)
        self.reset_entity_default_template(instance)
        self.sync_items(instance, items)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        items = validated_data.pop('items', None)
        instance = super().update(instance, validated_data)
        self.reset_entity_default_template(instance)
        if items is not None:
            self.sync_items(instance, items)
        return instance

    @staticmethod
    def reset_entity_default_template(instance: DataFactoryTemplate):
        if not instance.is_default:
            return
        DataFactoryTemplate.objects.filter(
            entity_id=instance.entity_id,
            is_default=True,
        ).exclude(id=instance.id).update(is_default=False)

    @staticmethod
    def sync_items(instance: DataFactoryTemplate, items: list):
        keep_ids = []
        for index, item in enumerate(items or []):
            item_data = dict(item)
            item_id = item_data.pop('id', None)
            child_template = item_data.get('child_template')
            if child_template and child_template.id == instance.id:
                raise serializers.ValidationError("场景模板不能关联自身")
            item_data['template'] = instance
            if item_data.get('sort') is None:
                item_data['sort'] = index
            if not item_data.get('name') and child_template:
                item_data['name'] = child_template.name
            if instance.update_user_id and not item_data.get('update_user'):
                item_data['update_user'] = instance.update_user
            if item_id:
                item_obj = DataFactoryTemplateItem.objects.filter(id=item_id, template=instance).first()
                if not item_obj:
                    raise serializers.ValidationError("关联模板不存在或不属于当前场景模板")
                for field, value in item_data.items():
                    setattr(item_obj, field, value)
                item_obj.save()
                keep_ids.append(item_obj.id)
            else:
                item_obj = DataFactoryTemplateItem.objects.create(**item_data)
                keep_ids.append(item_obj.id)
        DataFactoryTemplateItem.objects.filter(template=instance).exclude(id__in=keep_ids).delete()


class DataFactoryTemplateSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, cache_representation=True, read_only=True)
    module = RelatedObjectField(formatter=format_product_module_compact, read_only=True)
    entity = DataFactoryEntitySerializerC(read_only=True)
    items = DataFactoryTemplateItemSerializerC(many=True, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = DataFactoryTemplate
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return TestCenterQuerySelector.with_project_product_display(ProductModuleService.with_full_paths(
            queryset,
            'module',
            'entity__module',
        ).select_related(
            'project_product',
            'project_product__project',
            'entity',
            'entity__project_product',
            'entity__project_product__project',
            'entity__datasource_alias',
            'entity__datasource_alias__project_product',
            'update_user',
        ).prefetch_related('items', 'items__child_template', 'items__child_template__entity'))
