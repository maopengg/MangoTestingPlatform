# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂模板视图

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet
from pydantic import ValidationError

from src.auto_test.auto_data_factory.models import DataFactoryTemplate
from src.auto_test.auto_data_factory.service.cleanup import DataFactoryCleanup
from src.auto_test.auto_data_factory.service.runner import DataFactoryRunner
from src.auto_test.auto_data_factory.views.entity import DataFactoryEntitySerializerC
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.auto_test.auto_system.views.product_module import ProductModuleSerializersC
from src.exceptions import ToolsError
from src.models.data_factory_model import DataFactoryFieldOverrideRules, DataFactoryOutputConfig
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import RESPONSE_MSG_0001


class DataFactoryTemplateSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

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
            raise serializers.ValidationError("状态模板必须绑定模块")
        if project_product and module and module.project_product_id != project_product.id:
            raise serializers.ValidationError("模块不属于当前项目/产品")
        if project_product and entity and entity.project_product_id != project_product.id:
            raise serializers.ValidationError("实体不属于当前项目/产品")
        if module and entity and entity.module_id and entity.module_id != module.id:
            raise serializers.ValidationError("实体不属于当前模块")
        if entity and name:
            queryset = DataFactoryTemplate.objects.filter(entity=entity, name=name)
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            if queryset.exists():
                raise serializers.ValidationError(f"当前实体下已存在模板名称：{name}")
        field_overrides = attrs.get('field_overrides', self.instance.field_overrides if self.instance else {})
        try:
            DataFactoryFieldOverrideRules.model_validate(field_overrides or {})
        except ValidationError as error:
            raise serializers.ValidationError(f"字段覆盖规则格式错误：{error}") from error
        output_config = attrs.get('output_config', self.instance.output_config if self.instance else [])
        try:
            DataFactoryOutputConfig.model_validate(output_config or [])
        except ValidationError as error:
            raise serializers.ValidationError(f"输出配置格式错误：{error}") from error
        return attrs


class DataFactoryTemplateSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    module = ProductModuleSerializersC(read_only=True)
    entity = DataFactoryEntitySerializerC(read_only=True)

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
        )


class DataFactoryTemplateCRUD(ModelCRUD):
    model = DataFactoryTemplate
    queryset = DataFactoryTemplate.objects.all()
    serializer_class = DataFactoryTemplateSerializerC
    serializer = DataFactoryTemplateSerializer

    def post(self, request: Request):
        duplicated = self.get_duplicated_template(request.data)
        if duplicated:
            return ResponseData.fail((300, f"当前实体下已存在模板名称：{duplicated.name}，请编辑已有模板或更换名称"))
        return super().post(request)

    def put(self, request: Request):
        duplicated = self.get_duplicated_template(request.data, request.data.get('id'))
        if duplicated:
            return ResponseData.fail((300, f"当前实体下已存在模板名称：{duplicated.name}，请编辑已有模板或更换名称"))
        return super().put(request)

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
            status=source.status,
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
    def preview(self, request: Request):
        result = DataFactoryRunner.preview_template(
            template_id=request.data.get('template_id'),
            overrides=request.data.get('overrides') or {},
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
        return ResponseData.success(RESPONSE_MSG_0001, result)
