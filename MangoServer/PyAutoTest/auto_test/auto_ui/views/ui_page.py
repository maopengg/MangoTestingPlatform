# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023-01-15 10:56
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import UiPage
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD, ModelQuery


class UiPageSerializers(serializers.ModelSerializer):
    class Meta:
        model = UiPage
        fields = '__all__'  # 全部进行序列化
        # fields = ['project']  # 选中部分进行序列化
        # exclude = ['name']  # 除了这个字段，其他全序列化


class UiPageSerializersC(serializers.ModelSerializer):
    project = ProjectSerializers(read_only=True)

    class Meta:
        model = UiPage
        fields = '__all__'


class UiPageQuery(ModelQuery):
    """
    条件查
    """
    model = UiPage
    serializer_class = UiPageSerializersC


class UiPageCRUD(ModelCRUD):
    model = UiPage
    queryset = UiPage.objects.all()
    serializer_class = UiPageSerializersC
    # post专用序列化器
    serializer = UiPageSerializers


class UiPageViews(ViewSet):
    model = UiPage
    serializer_class = UiPageSerializers

    @action(methods=['GET'], detail=False)
    def get_page_name_all(self, request: Request):
        """
        获取所有的页面名称
        """
        res = UiPage.objects.values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success('获取数据成功', data)

    @action(methods=['GET'], detail=False)
    def get_page_name_project(self, request: Request):
        """
        根据项目获取页面id和名称
        """
        res = UiPage.objects.filter(project=request.query_params.get('project_id')).values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        if data:
            return ResponseData.success('获取数据成功', data)

        else:
            return ResponseData.fail('该选择的项目暂无页面，清先建立页面并收集页面元素')
