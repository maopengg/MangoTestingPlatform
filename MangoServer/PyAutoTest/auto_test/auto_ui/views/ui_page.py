# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description:
# @Time   : 2023-01-15 10:56
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import UiPage
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD, ModelR


class UiPageSerializers(serializers.ModelSerializer):
    class Meta:
        model = UiPage
        fields = '__all__'  # 全部进行序列化
        # fields = ['project']  # 选中部分进行序列化
        # exclude = ['name']  # 除了这个字段，其他全序列化


class UiPageSerializersC(serializers.ModelSerializer):
    team = ProjectSerializers(read_only=True)

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
    serializer_class = UiPageSerializersC
    # post专用序列化器
    serializer = UiPageSerializers


class UiPageViews(ViewSet):
    model = UiPage
    serializer_class = UiPageSerializers

    @action(methods=['GET'], detail=False)
    def get_page_name(self, request: Request):
        """
        获取所有的页面名称
        """
        res = UiPage.objects.values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return Response({
            'code': 200,
            'msg': '获取数据成功',
            'data': data
        })
