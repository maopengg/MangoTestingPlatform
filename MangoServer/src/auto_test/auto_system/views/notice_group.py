# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
import json

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from mangotools.enums import NoticeEnum
from src.auto_test.auto_system.models import NoticeGroup
from src.auto_test.auto_system.views.project import ProjectSerializers
from src.auto_test.auto_user.models import User
from src.auto_test.auto_user.views.user import UserSerializers
from src.enums.tools_enum import StatusEnum
from src.exceptions import MangoServerError
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class NoticeGroupSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = NoticeGroup
        fields = '__all__'


class NoticeGroupSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    users = UserSerializers(read_only=True, many=True)

    class Meta:
        model = NoticeGroup
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product'
        ).prefetch_related(
            'users'
        )
        return queryset


class NoticeGroupCRUD(ModelCRUD):
    model = NoticeGroup
    queryset = NoticeGroup.objects.all()
    serializer_class = NoticeGroupSerializersC
    serializer = NoticeGroupSerializers


class NoticeGroupViews(ViewSet):
    model = NoticeGroup
    queryset = NoticeGroup.objects.all()
    serializer_class = NoticeGroupSerializersC
    serializer = NoticeGroupSerializers

    @action(methods=['get'], detail=False)
    @error_response('system')
    def test(self, request: Request):
        from src.auto_test.auto_system.service.notice import NoticeMain
        _id = request.query_params.get('id')
        try:
            # NoticeMain.notice_main(2, 2, 197899881973)
            NoticeMain.test_notice_send(_id)
        except MangoServerError as error:
            return ResponseData.fail((error.code, error.msg))
        else:
            return ResponseData.success(RESPONSE_MSG_0046)
