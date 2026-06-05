# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: API用例数据工厂配置视图

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_data_factory.models import DataFactoryCaseConfig
from src.apps.auto_data_factory.service.runner import DataFactoryRunner
from src.apps.auto_data_factory.views.template import DataFactoryTemplateSerializerC
from src.common.enums.data_factory_enum import DataFactoryCaseSourceTypeEnum
from src.common.exceptions import ToolsError
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0013


class ApiCaseDataFactorySerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    case = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = DataFactoryCaseConfig
        fields = '__all__'

    def to_internal_value(self, data):
        data = data.copy()
        if data.get('cleanup_strategy') == "":
            data['cleanup_strategy'] = None
        if data.get('case') is not None and data.get('source_id') is None:
            data['source_id'] = data.get('case')
        data['source_type'] = DataFactoryCaseSourceTypeEnum.API_CASE.value
        return super().to_internal_value(data)

    def validate(self, attrs):
        if attrs.get('cleanup_strategy') == "":
            attrs['cleanup_strategy'] = None
        return attrs


class ApiCaseDataFactorySerializerC(serializers.ModelSerializer):
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


class ApiCaseDataFactoryCRUD(ModelCRUD):
    model = DataFactoryCaseConfig
    queryset = DataFactoryCaseConfig.objects.all()
    serializer_class = ApiCaseDataFactorySerializerC
    serializer = ApiCaseDataFactorySerializer
    not_matching_str = ModelCRUD.not_matching_str + ['case', 'template', 'source_type', 'source_id']

    @error_response('api')
    def get(self, request: Request):
        case_id = request.query_params.get('case') or request.query_params.get('source_id')
        queryset = DataFactoryCaseConfig.objects.filter(
            source_type=DataFactoryCaseSourceTypeEnum.API_CASE.value,
        )
        if case_id:
            queryset = queryset.filter(source_id=case_id)
        queryset = ApiCaseDataFactorySerializerC.setup_eager_loading(queryset).order_by('sort', 'id')
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ApiCaseDataFactorySerializerC(instance=queryset, many=True).data,
            queryset.count(),
        )


class ApiCaseDataFactoryViews(ViewSet):
    @action(methods=['put'], detail=False)
    @error_response('api')
    def put_case_sort(self, request: Request):
        for item in request.data.get('case_sort_list', []):
            obj = DataFactoryCaseConfig.objects.get(
                id=item['id'],
                source_type=DataFactoryCaseSourceTypeEnum.API_CASE.value,
            )
            obj.sort = item['sort']
            obj.save(update_fields=['sort', 'update_time'])
        return ResponseData.success(RESPONSE_MSG_0013)

    @action(methods=['post'], detail=False)
    @error_response('api')
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
