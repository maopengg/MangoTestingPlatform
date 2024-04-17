# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-10-12 18:14
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_user.models import ProjectModule, User
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *


class ProjectModuleSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ProjectModule
        fields = '__all__'


class ProjectModuleSerializersC(serializers.ModelSerializer):
    project = ProjectSerializers(read_only=True)
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ProjectModule
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project')
        return queryset


class ProjectModuleCRUD(ModelCRUD):
    model = ProjectModule
    queryset = ProjectModule.objects.all()
    serializer_class = ProjectModuleSerializersC
    # post专用序列化器
    serializer = ProjectModuleSerializers


class ProjectModuleViews(ViewSet):
    model = ProjectModule
    serializer_class = ProjectModuleSerializers

    @action(methods=['GET'], detail=False)
    def get_module_name_all(self, request: Request):
        project_id = request.query_params.get('project_id')
        if project_id is None:
            project_id = User.objects.get(id=request.user['id']).selected_project
        if project_id:
            res = self.model.objects.values_list('id', 'name').filter(project=project_id)
        else:
            res = self.model.objects.values_list('id', 'name').all()
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success(RESPONSE_MSG_0031, data)
