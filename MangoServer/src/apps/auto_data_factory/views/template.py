# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂模板视图

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet
from copy import deepcopy

from pydantic import ValidationError
from django.db import transaction

from src.apps.auto_data_factory.models import DataFactoryTemplate, DataFactoryTemplateItem
from src.apps.auto_data_factory.service.cleanup import DataFactoryCleanup
from src.apps.auto_data_factory.service.runner import DataFactoryRunner
from src.apps.auto_data_factory.views.entity import DataFactoryEntitySerializerC
from src.common.enums.data_factory_enum import DataFactoryTemplateConfigStatusEnum
from src.apps.auto_system.views.project_product import ProjectProductSerializersC
from src.apps.auto_system.views.product_module import ProductModuleSerializersC
from src.common.exceptions import DataFactoryError, ToolsError
from src.common.exceptions.error_msg import (
    DATA_FACTORY_ERROR_0001,
    DATA_FACTORY_ERROR_0002,
    DATA_FACTORY_ERROR_0003,
    DATA_FACTORY_ERROR_0004,
    DATA_FACTORY_ERROR_0005,
    DATA_FACTORY_ERROR_0006,
    DATA_FACTORY_ERROR_0007,
)
from src.common.models.data_factory_model import DataFactoryFieldOverrideRules, DataFactoryOutputConfig
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0002, RESPONSE_MSG_0003, RESPONSE_MSG_0004, \
    RESPONSE_MSG_0082, RESPONSE_MSG_0005


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


class DataFactoryTemplateSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    items = DataFactoryTemplateItemSerializer(many=True, required=False)

    class Meta:
        model = DataFactoryTemplate
        fields = '__all__'
        validators = []

    def validate(self, attrs):
        project_product = attrs.get('project_product', self.instance.project_product if self.instance else None)
        module = attrs.get('module', self.instance.module if self.instance else None)
        entity = attrs.get('entity', self.instance.entity if self.instance else None)
        name = attrs.get('name', self.instance.name if self.instance else None)
        if not module:
            raise DataFactoryError(*DATA_FACTORY_ERROR_0001)
        if project_product and module and module.project_product_id != project_product.id:
            raise DataFactoryError(*DATA_FACTORY_ERROR_0002)
        if project_product and entity and entity.project_product_id != project_product.id:
            raise DataFactoryError(*DATA_FACTORY_ERROR_0003)
        if module and entity and entity.module_id and entity.module_id != module.id:
            raise DataFactoryError(*DATA_FACTORY_ERROR_0004)
        if entity and name:
            queryset = DataFactoryTemplate.objects.filter(entity=entity, name=name)
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            if queryset.exists():
                raise DataFactoryError(*DATA_FACTORY_ERROR_0005, value=(name,))
        field_overrides = attrs.get('field_overrides', self.instance.field_overrides if self.instance else {})
        try:
            attrs['field_overrides'] = DataFactoryFieldOverrideRules.model_validate(field_overrides or {}).model_dump()
        except ValidationError as error:
            raise DataFactoryError(*DATA_FACTORY_ERROR_0006, value=(error,)) from error
        output_config = attrs.get('output_config', self.instance.output_config if self.instance else [])
        try:
            attrs['output_config'] = DataFactoryOutputConfig.model_validate(output_config or []).model_dump()
        except ValidationError as error:
            raise DataFactoryError(*DATA_FACTORY_ERROR_0007, value=(error,)) from error
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
    project_product = ProjectProductSerializersC(read_only=True)
    module = ProductModuleSerializersC(read_only=True)
    entity = DataFactoryEntitySerializerC(read_only=True)
    items = DataFactoryTemplateItemSerializerC(many=True, read_only=True)

    class Meta:
        model = DataFactoryTemplate
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'project_product',
            'project_product__project',
            'module',
            'entity',
            'entity__project_product',
            'entity__project_product__project',
            'entity__datasource_alias',
            'entity__datasource_alias__project_product',
        ).prefetch_related('items', 'items__child_template', 'items__child_template__entity')


class DataFactoryTemplateCRUD(ModelCRUD):
    model = DataFactoryTemplate
    queryset = DataFactoryTemplate.objects.all()
    serializer_class = DataFactoryTemplateSerializerC
    serializer = DataFactoryTemplateSerializer
    not_matching_str = ModelCRUD.not_matching_str + ['entity', 'usage_scope']

    @error_response('system')
    def post(self, request: Request):
        duplicated = self.get_duplicated_template(request.data)
        if duplicated:
            raise DataFactoryError(*DATA_FACTORY_ERROR_0005, value=(duplicated.name,))
        data = request.data.copy()
        test_env = data.pop('test_env', None)
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            instance = serializer.save()
            self.refresh_config_status(instance, test_env)
            return ResponseData.success(RESPONSE_MSG_0002, self.serializer(instance).data)
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)

    @error_response('system')
    def put(self, request: Request):
        duplicated = self.get_duplicated_template(request.data, request.data.get('id'))
        if duplicated:
            raise DataFactoryError(*DATA_FACTORY_ERROR_0005, value=(duplicated.name,))
        data = request.data.copy()
        test_env = data.pop('test_env', None)
        serializer = self.serializer(
            instance=self.model.objects.get(pk=data.get('id')),
            data=data,
            partial=True,
        )
        if serializer.is_valid():
            instance = serializer.save()
            self.refresh_config_status(instance, test_env)
            return ResponseData.success(RESPONSE_MSG_0082, self.serializer(instance).data)
        return ResponseData.fail(RESPONSE_MSG_0004, serializer.errors)

    @staticmethod
    def get_duplicated_template(data: dict, exclude_id=None):
        entity = data.get('entity')
        name = data.get('name')
        if not entity or not name:
            return None
        queryset = DataFactoryTemplate.objects.filter(entity_id=entity, name=name)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.first()

    @staticmethod
    def refresh_config_status(template: DataFactoryTemplate, test_env=None):
        try:
            result = DataFactoryRunner.preview_template(
                template_id=template.id,
                overrides=template.field_overrides or {},
                output_config=template.output_config,
                test_env=test_env,
            )
            config_status = (
                DataFactoryTemplateConfigStatusEnum.READY.value
                if result.get('can_debug_run')
                else DataFactoryTemplateConfigStatusEnum.INCOMPLETE.value
            )
        except Exception:
            config_status = DataFactoryTemplateConfigStatusEnum.INCOMPLETE.value
        if template.config_status != config_status:
            template.config_status = config_status
            template.save(update_fields=['config_status', 'update_time'])


class DataFactoryTemplateViews(ViewSet):
    @action(methods=['post'], detail=False)
    @error_response('system')
    def copy(self, request: Request):
        source = DataFactoryTemplate.objects.get(id=request.data.get('id'))
        target = DataFactoryTemplate.objects.create(
            project_product=source.project_product,
            module=source.module,
            entity=source.entity,
            name=request.data.get('name') or f"{source.name}_副本",
            description=source.description,
            field_overrides=source.field_overrides,
            output_config=source.output_config,
            cleanup_strategy=source.cleanup_strategy,
            is_default=False,
            usage_scope=source.usage_scope,
            status=source.status,
        )
        for item in source.items.all():
            DataFactoryTemplateItem.objects.create(
                template=target,
                child_template=item.child_template,
                name=item.name,
                sort=item.sort,
                field_overrides=deepcopy(item.field_overrides or {}),
            )
        return ResponseData.success(RESPONSE_MSG_0001, DataFactoryTemplateSerializer(target).data)

    @action(methods=['put'], detail=False)
    @error_response('system')
    def status(self, request: Request):
        template = DataFactoryTemplate.objects.get(id=request.data.get('id'))
        if request.data.get('status') is None:
            raise ToolsError(300, "状态不能为空")
        template.status = request.data.get('status')
        template.save(update_fields=['status', 'update_time'])
        return ResponseData.success(RESPONSE_MSG_0001, DataFactoryTemplateSerializer(template).data)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def sync_fields(self, request: Request):
        template = DataFactoryTemplate.objects.select_related('entity').get(id=request.data.get('id'))
        fields = template.entity.datafactoryfield_set.all().order_by('sort', 'id')
        template.field_overrides = {
            field.name: {
                "generator_type": field.generator_type,
                "generator_config": deepcopy(field.generator_config or {}),
            }
            for field in fields
        }
        template.save(update_fields=['field_overrides', 'update_time'])
        DataFactoryTemplateCRUD.refresh_config_status(template, request.data.get('test_env'))
        return ResponseData.success(RESPONSE_MSG_0001, DataFactoryTemplateSerializer(template).data)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def preview(self, request: Request):
        result = DataFactoryRunner.preview_template(
            template_id=request.data.get('template_id'),
            overrides=request.data.get('overrides') or {},
            output_config=request.data.get('output_config'),
            context=request.data.get('context') or {},
            test_object_id=request.data.get('test_object_id'),
            test_env=request.data.get('test_env'),
        )
        return ResponseData.success(RESPONSE_MSG_0001, result)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def debug_run(self, request: Request):
        result = DataFactoryRunner.debug_run_template(
            template_id=request.data.get('template_id'),
            overrides=request.data.get('overrides') or {},
            context=request.data.get('context') or {},
            test_object_id=request.data.get('test_object_id'),
            test_env=request.data.get('test_env'),
        )
        return ResponseData.success(RESPONSE_MSG_0001, result)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def debug_cleanup(self, request: Request):
        result = DataFactoryCleanup.cleanup_execution(request.data.get('execution_id'))
        return ResponseData.success(RESPONSE_MSG_0005, result)
