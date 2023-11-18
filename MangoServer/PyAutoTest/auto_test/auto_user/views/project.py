# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 项目表
# @Time   : 2023-03-03 12:21
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD
from ..models import Project


class ProjectSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = Project
        fields = '__all__'  # 全部进行序列化


class ProjectCRUD(ModelCRUD):
    model = Project
    queryset = Project.objects.all()
    serializer_class = ProjectSerializers
    serializer = ProjectSerializers


class ProjectViews(ViewSet):
    model = Project
    serializer_class = ProjectSerializers

    @action(methods=['get'], detail=False)
    def get_all_items(self, request: Request):
        items = Project.objects.filter(status=1)
        data = [{'title': i.name, 'key': i.pk} for i in items]
        return ResponseData.success('获取所有项目名称成功', data)
