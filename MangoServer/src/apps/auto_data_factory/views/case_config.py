# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂用例配置视图

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet
from pydantic import ValidationError

from src.apps.auto_data_factory.models import DataFactoryCaseConfig
from src.apps.auto_data_factory.service.runner import DataFactoryRunner
from src.apps.auto_data_factory.views.template import DataFactoryTemplateSerializerC
from src.common.enums.data_factory_enum import DataFactoryCaseSourceTypeEnum, DataFactoryTemplateUsageScopeEnum
from src.common.exceptions import ToolsError
from src.common.models.data_factory_model import validate_data_factory_scene_overrides
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0013


class DataFactoryCaseConfigSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = DataFactoryCaseConfig
        fields = '__all__'

    def to_internal_value(self, data):
        data = data.copy()
        if data.get('cleanup_strategy') == "":
            data['cleanup_strategy'] = None
        if data.get('case') is not None and data.get('source_id') is None:
            data['source_id'] = data.get('case')
        return super().to_internal_value(data)

    def validate(self, attrs):
        source_type = attrs.get('source_type', self.instance.source_type if self.instance else None)
        if source_type not in DataFactoryCaseSourceTypeEnum.obj():
            raise serializers.ValidationError("用例来源类型不正确")
        if not attrs.get('source_id', self.instance.source_id if self.instance else None):
            raise serializers.ValidationError("用例ID不能为空")
        if attrs.get('cleanup_strategy') == "":
            attrs['cleanup_strategy'] = None
        template = attrs.get('template', self.instance.template if self.instance else None)
        if template and template.usage_scope == DataFactoryTemplateUsageScopeEnum.INTERNAL.value:
            raise serializers.ValidationError("仅场景内部引用用途的场景模板不能绑定到用例")
        field_overrides = attrs.get('field_overrides', self.instance.field_overrides if self.instance else {})
        try:
            attrs['field_overrides'] = validate_data_factory_scene_overrides(field_overrides or {})
        except (ValidationError, ValueError) as error:
            raise serializers.ValidationError(f"字段覆盖规则格式错误：{error}") from error
        return attrs


class DataFactoryCaseConfigSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    template = DataFactoryTemplateSerializerC(read_only=True)
    case = serializers.IntegerField(source='source_id', read_only=True)

    class Meta:
        model = DataFactoryCaseConfig
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'template',
            'template__project_product',
            'template__project_product__project',
            'template__entity',
            'template__entity__project_product',
            'template__entity__project_product__project',
            'template__entity__datasource_alias',
            'template__entity__datasource_alias__project_product',
        )


class DataFactoryCaseConfigCRUD(ModelCRUD):
    model = DataFactoryCaseConfig
    queryset = DataFactoryCaseConfig.objects.all()
    serializer_class = DataFactoryCaseConfigSerializerC
    serializer = DataFactoryCaseConfigSerializer
    not_matching_str = ModelCRUD.not_matching_str + ['template']

    @error_response('system')
    def get(self, request: Request):
        source_type = request.query_params.get('source_type')
        source_id = request.query_params.get('source_id') or request.query_params.get('case')
        if not source_type:
            raise ToolsError(300, "用例来源类型不能为空")
        queryset = DataFactoryCaseConfig.objects.filter(source_type=source_type)
        if source_id:
            queryset = queryset.filter(source_id=source_id)
        queryset = DataFactoryCaseConfigSerializerC.setup_eager_loading(queryset).order_by('sort', 'id')
        return ResponseData.success(
            RESPONSE_MSG_0001,
            DataFactoryCaseConfigSerializerC(instance=queryset, many=True).data,
            queryset.count(),
        )


class DataFactoryCaseConfigViews(ViewSet):
    @action(methods=['put'], detail=False)
    @error_response('system')
    def put_case_sort(self, request: Request):
        source_type = request.data.get('source_type')
        if not source_type:
            raise ToolsError(300, "用例来源类型不能为空")
        for item in request.data.get('case_sort_list', []):
            obj = DataFactoryCaseConfig.objects.get(
                id=item['id'],
                source_type=source_type,
            )
            obj.sort = item['sort']
            obj.save(update_fields=['sort', 'update_time'])
        return ResponseData.success(RESPONSE_MSG_0013)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def preview(self, request: Request):
        template_id = request.data.get('template_id')
        if not template_id:
            raise ToolsError(300, "状态模板不能为空")
        result = DataFactoryRunner.preview_template(
            template_id=template_id,
            overrides=request.data.get('field_overrides') or {},
            context=request.data.get('context') or {},
            test_object_id=request.data.get('test_object_id'),
            test_env=request.data.get('test_env'),
        )
        return ResponseData.success(RESPONSE_MSG_0001, result)
