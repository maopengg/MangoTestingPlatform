# -*- coding: utf-8 -*-
# @ProjectProduct: MangoServer
# @Description: 项目表
# @Time   : 2023-03-03 12:21
# @Author : 毛鹏
import logging

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *
from .project import ProjectSerializers
from ..models import ProjectProduct

log = logging.getLogger('user')


class ProjectProductSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ProjectProduct
        fields = '__all__'


class ProjectProductSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project = ProjectSerializers(read_only=True)

    class Meta:
        model = ProjectProduct
        fields = '__all__'  # 全部进行序列化

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project')
        return queryset


class ProjectProductCRUD(ModelCRUD):
    model = ProjectProduct
    queryset = ProjectProduct.objects.all()
    serializer_class = ProjectProductSerializersC
    serializer = ProjectProductSerializers


class ProjectProductViews(ViewSet):
    model = ProjectProduct
    serializer_class = ProjectProductSerializers

    @action(methods=['GET'], detail=False)
    def get_project_name(self, request: Request):
        project_id = request.query_params.get('project_id')
        if project_id:
            res = self.model.objects.values_list('id', 'name').filter(project=project_id)
        else:
            res = self.model.objects.values_list('id', 'name').all()
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success(RESPONSE_MSG_0118, data)
