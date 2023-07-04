# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import NoticeConfig
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.enums.system_enum import NoticeEnum
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD
from PyAutoTest.utils.view_utils.view_tools import enum_list


class NoticeConfigSerializers(serializers.ModelSerializer):
    team = ProjectSerializers(read_only=True)

    class Meta:
        model = NoticeConfig
        fields = '__all__'


class NoticeConfigSerializersC(serializers.ModelSerializer):
    class Meta:
        model = NoticeConfig
        fields = '__all__'


class NoticeConfigCRUD(ModelCRUD):
    model = NoticeConfig
    queryset = NoticeConfig.objects.all()
    serializer_class = NoticeConfigSerializers
    serializer = NoticeConfigSerializersC


class NoticeConfigViews(ViewSet):
    model = NoticeConfig
    queryset = NoticeConfig.objects.all()
    serializer_class = NoticeConfigSerializers
    serializer = NoticeConfigSerializersC

    @action(methods=['get'], detail=False)
    def test(self, request):
        from PyAutoTest.auto_test.auto_system.service.notic_tools import notice_main
        _id = request.query_params.get('id')
        team_id = request.query_params.get('team_id')
        notice_main(team_id, _id)
        return Response({
            'code': 200,
            'msg': '通知发送成功',
            'data': None
        })

    @action(methods=['get'], detail=False)
    def get_notice_type(self, request):
        return Response({
            'code': 200,
            'msg': '获取通知类型成功',
            'data': enum_list(NoticeEnum)
        })

    # @action(methods=['get'], detail=False)
    # def up_notice_state(self, request):
    #     state = {request.query_params.get('state')}
