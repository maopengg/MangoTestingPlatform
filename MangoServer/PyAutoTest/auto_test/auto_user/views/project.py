# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 项目组表
# @Time   : 2023-03-03 12:21
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.utils.view_utils.model_crud import ModelCRUD
from ..models import Project


class ProjectSerializers(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'  # 全部进行序列化


class ProjectCRUD(ModelCRUD):
    model = Project
    queryset = Project.objects.all()
    serializer_class = ProjectSerializers


class ProjectViews(ViewSet):

    @action(methods=['get'], detail=False)
    def get_all_items(self, request):
        items = Project.objects.all()
        data = [{'title': i.name, 'key': i.pk} for i in items]
        return Response({
            'code': 200,
            'data': data,
            'msg': '获取所有项目组名称成功'
        })
