# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-17 21:39
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.models import ApiPublic
from src.apps.auto_data_factory.views.datasource_alias import DataFactoryDatasourceAliasSerializerC
from src.apps.auto_system.views.project_product import ProjectProductSerializersC
from src.common.enums.api_enum import ApiPublicTypeEnum
from src.common.enums.tools_enum import StatusEnum
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class ApiPublicSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiPublic
        fields = '__all__'

    def validate_type(self, value):
        if value not in ApiPublicTypeEnum.get_key_list():
            raise serializers.ValidationError('公共变量类型只支持自定义和SQL')
        return value

    def validate(self, attrs):
        public_type = attrs.get('type', self.instance.type if self.instance else None)
        datasource_alias = attrs.get(
            'datasource_alias',
            self.instance.datasource_alias if self.instance else None,
        )
        project_product = attrs.get(
            'project_product',
            self.instance.project_product if self.instance else None,
        )
        if public_type == ApiPublicTypeEnum.SQL.value and not datasource_alias:
            raise serializers.ValidationError('SQL公共变量必须选择逻辑数据源')
        if datasource_alias and project_product and datasource_alias.project_product_id != project_product.id:
            raise serializers.ValidationError('逻辑数据源不属于当前项目产品')
        return attrs


class ApiPublicSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    datasource_alias = DataFactoryDatasourceAliasSerializerC(read_only=True)

    class Meta:
        model = ApiPublic
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'datasource_alias')
        return queryset


class ApiPublicCRUD(ModelCRUD):
    model = ApiPublic
    queryset = ApiPublic.objects.filter(type__in=ApiPublicTypeEnum.get_key_list())
    serializer_class = ApiPublicSerializersC
    serializer = ApiPublicSerializers
    not_matching_str = ModelCRUD.not_matching_str + ['test_env', 'datasource_alias']


class ApiPublicViews(ViewSet):
    model = ApiPublic
    serializer_class = ApiPublicSerializers

    @action(methods=['put'], detail=False)
    @error_response('api')
    def put_status(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """

        obj = self.model.objects.get(id=request.data.get('id'))
        obj.status = request.data.get('status')
        obj.save()
        return ResponseData.success(RESPONSE_MSG_0104, )
