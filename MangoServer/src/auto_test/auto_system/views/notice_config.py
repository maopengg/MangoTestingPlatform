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
from src.auto_test.auto_system.models import NoticeConfig
from src.auto_test.auto_system.views.project import ProjectSerializers
from src.auto_test.auto_user.models import User
from src.enums.tools_enum import StatusEnum
from src.exceptions import MangoServerError
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


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
        from src.auto_test.auto_system.service.notice import NoticeMain
        _id = request.query_params.get('id')
        try:
            # NoticeMain.notice_main(2, 2, 197899881973)
            NoticeMain.test_notice_send(_id)
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
        obj_ = self.model.objects.get(id=request.data.get('id'))
        if obj_.config is None or obj_.config == '':
            return ResponseData.fail(RESPONSE_MSG_0126)
        if request.data.get('status') == StatusEnum.SUCCESS.value:
            if obj_.type == NoticeEnum.MAIL.value:
                try:
                    config = json.loads(obj_.config)
                    if not isinstance(config, dict) and not isinstance(config, list):
                        return ResponseData.fail(RESPONSE_MSG_0130, )
                except (TypeError, json.decoder.JSONDecodeError):
                    return ResponseData.fail(RESPONSE_MSG_0130, )
                for i in config:
                    try:
                        user = User.objects.get(name=i)
                    except User.DoesNotExist:
                        return ResponseData.fail(RESPONSE_MSG_0125)
                    if user.mailbox is None or user.mailbox == []:
                        return ResponseData.fail(RESPONSE_MSG_0125, )
            obj = self.model.objects.filter(test_object=request.data.get('test_object')).values('status')
            if any(item['status'] == 1 for item in obj):
                return ResponseData.fail(RESPONSE_MSG_0119, )
        obj_.status = request.data.get('status')
        obj_.save()
        return ResponseData.success(RESPONSE_MSG_0047, )
