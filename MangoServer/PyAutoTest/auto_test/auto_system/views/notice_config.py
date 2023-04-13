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
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class NoticeConfigSerializers(serializers.ModelSerializer):
    team = ProjectSerializers(read_only=True)

    class Meta:
        model = NoticeConfig
        fields = '__all__'


class NoticeConfigCRUD(ModelCRUD):
    model = NoticeConfig
    queryset = NoticeConfig.objects.select_related('team').all()
    serializer_class = NoticeConfigSerializers


class NoticeConfigViews(ViewSet):

    @action(methods=['get'], detail=False)
    def test(self, request):
        from ..notic_tools import notice_main
        notice_main(request.query_params.get('name'))
        return Response({
            'code': 0,
            'msg': '通知发送成功',
            'data': None
        })
