# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-03-25 18:53
# @Author : 毛鹏

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import Database
from PyAutoTest.auto_test.auto_ui.models import UiPublic
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *


class UiPublicSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UiPublic
        fields = '__all__'


class UiPublicSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project = ProjectSerializers(read_only=True)

    class Meta:
        model = UiPublic
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.prefetch_related(
            'project')
        return queryset


class UiPublicCRUD(ModelCRUD):
    model = UiPublic
    queryset = UiPublic.objects.select_related('project').all()
    serializer_class = UiPublicSerializersC
    serializer = UiPublicSerializers


class UiPublicViews(ViewSet):
    model = UiPublic
    serializer_class = UiPublicSerializers

    @action(methods=['put'], detail=False)
    def put_status(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """
        obj = self.model.objects.get(id=request.data.get('id'))
        if request.data.get('status') == StatusEnum.SUCCESS.value:
            try:
                Database.objects.get(project_id=obj.project.id)
            except Database.DoesNotExist:
                return ResponseData.fail(RESPONSE_MSG_0110, )
        obj.status = request.data.get('status')
        obj.save()
        return ResponseData.success(RESPONSE_MSG_0021, )
