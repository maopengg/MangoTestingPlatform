# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
import requests
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import NoticeConfig
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.tools.decorator.error_response import error_response
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *


class NoticeConfigSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = NoticeConfig
        fields = '__all__'


class NoticeConfigSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project = ProjectSerializers(read_only=True)

    class Meta:
        model = NoticeConfig
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project',
        )
        return queryset


class NoticeConfigCRUD(ModelCRUD):
    model = NoticeConfig
    queryset = NoticeConfig.objects.all()
    serializer_class = NoticeConfigSerializersC
    serializer = NoticeConfigSerializers


class NoticeConfigViews(ViewSet):
    model = NoticeConfig
    queryset = NoticeConfig.objects.all()
    serializer_class = NoticeConfigSerializersC
    serializer = NoticeConfigSerializers

    @action(methods=['get'], detail=False)
    @error_response('system')
    def test(self, request: Request):
        from PyAutoTest.auto_test.auto_system.service.notic_tools import NoticeMain
        _id = request.query_params.get('id')
        try:
            NoticeMain.test_notice_send(_id)
        except requests.exceptions.SSLError:
            return ResponseData.fail(RESPONSE_MSG_0045)
        except MangoServerError as error:
            return ResponseData.fail((error.code, error.msg))
        else:
            return ResponseData.success(RESPONSE_MSG_0046)

    @action(methods=['put'], detail=False)
    @error_response('system')
    def put_status(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """
        obj = self.model.objects.get(id=request.data.get('id'))
        if self.model.objects \
                .filter(project_id=obj.project_id, type=obj.type, status=StatusEnum.SUCCESS.value) \
                and request.data.get('status') == StatusEnum.SUCCESS.value:
            return ResponseData.success(RESPONSE_MSG_0119, )

        obj.status = request.data.get('status')
        obj.save()
        return ResponseData.success(RESPONSE_MSG_0047, )
