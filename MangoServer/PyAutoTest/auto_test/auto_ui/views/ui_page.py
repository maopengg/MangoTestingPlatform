# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description:
# @Time   : 2023-01-15 10:56
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import UiPage, UiElement
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD, ModelR


class UiPageSerializers(serializers.ModelSerializer):
    team = ProjectSerializers(read_only=True)

    class Meta:
        model = UiPage
        fields = '__all__'  # 全部进行序列化
        # fields = ['project']  # 选中部分进行序列化
        # exclude = ['name']  # 除了这个字段，其他全序列化


class UiPageSerializersC(serializers.ModelSerializer):
    class Meta:
        model = UiPage
        fields = '__all__'


class UiPageR(ModelR):
    """
    条件查
    """
    model = UiPage
    serializer_class = UiPageSerializers


class UiPageCRUD(ModelCRUD):
    model = UiPage
    queryset = UiPage.objects.all()
    serializer_class = UiPageSerializers
    # post专用序列化器
    serializer = UiPageSerializersC


class UiPageViews(ViewSet):

    @action(methods=['get'], detail=False)
    def get_page_name1(self, request):
        """
        获取所有的页面名称和元素
        @param request:
        @return:
        """
        data = []
        results = UiPage.objects.values_list('id', 'name')
        for result in results:
            page = {'label': result[1], 'value': result[0], 'children': []}
            for i in UiElement.objects.filter(page=result[0]):
                page['children'].append({'label': i.name, 'value': i.id})
            data.append(page)
        return Response({
            'code': 200,
            'msg': '获取数据成功~',
            'data': data
        })

    @action(methods=['GET'], detail=False)
    def get_page_name(self, request):
        data = []
        res = UiPage.objects.values_list('id', 'name')
        for _id, name in res:
            data.append({'value': _id, 'label': name})
        return Response({
            'code': 200,
            'msg': '获取数据成功~',
            'data': data
        })
