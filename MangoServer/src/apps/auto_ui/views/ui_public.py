# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-03-25 18:53
# @Author : 毛鹏

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_data_factory.views.datasource_alias import DataFactoryDatasourceAliasSerializerC
from src.apps.auto_system.views.project_product import ProjectProductSerializersC
from src.apps.auto_ui.models import UiPublic
from src.common.enums.ui_enum import UiPublicTypeEnum
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class UiPublicSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UiPublic
        fields = '__all__'

    def validate_type(self, value):
        if value not in UiPublicTypeEnum.get_key_list():
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
        if public_type == UiPublicTypeEnum.SQL.value and not datasource_alias:
            raise serializers.ValidationError('SQL公共变量必须选择逻辑数据源')
        if datasource_alias and project_product and datasource_alias.project_product_id != project_product.id:
            raise serializers.ValidationError('逻辑数据源不属于当前项目产品')
        return attrs


class UiPublicSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    datasource_alias = DataFactoryDatasourceAliasSerializerC(read_only=True)

    class Meta:
        model = UiPublic
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'datasource_alias')
        return queryset


class UiPublicCRUD(ModelCRUD):
    model = UiPublic
    queryset = UiPublic.objects.filter(type__in=UiPublicTypeEnum.get_key_list())
    serializer_class = UiPublicSerializersC
    serializer = UiPublicSerializers
    not_matching_str = ModelCRUD.not_matching_str + ['test_env', 'datasource_alias']


class UiPublicViews(ViewSet):
    model = UiPublic
    serializer_class = UiPublicSerializers

    @action(methods=['put'], detail=False)
    @error_response('ui')
    def put_status(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """
        obj = self.model.objects.get(id=request.data.get('id'))
        obj.status = request.data.get('status')
        obj.save()
        return ResponseData.success(RESPONSE_MSG_0021, )
