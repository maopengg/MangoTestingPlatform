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
from PyAutoTest.enums.system_enum import NoticeEnum
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD, ModelQuery
from PyAutoTest.tools.view_utils.view_tools import enum_list


class NoticeConfigSerializers(serializers.ModelSerializer):
    class Meta:
        model = NoticeConfig
        fields = '__all__'


class NoticeConfigSerializersC(serializers.ModelSerializer):
    project = ProjectSerializers(read_only=True)

    class Meta:
        model = NoticeConfig
        fields = '__all__'


class NoticeConfigCRUD(ModelCRUD):
    model = NoticeConfig
    queryset = NoticeConfig.objects.all()
    serializer_class = NoticeConfigSerializersC
    serializer = NoticeConfigSerializers


class NoticeConfigQuery(ModelQuery):
    model = NoticeConfig
    serializer_class = NoticeConfigSerializersC


class NoticeConfigViews(ViewSet):
    model = NoticeConfig
    queryset = NoticeConfig.objects.all()
    serializer_class = NoticeConfigSerializersC
    serializer = NoticeConfigSerializers

    @action(methods=['get'], detail=False)
    def test(self, request: Request):
        from PyAutoTest.auto_test.auto_system.service.notic_tools import NoticeMain
        _id = request.query_params.get('id')
        try:
            NoticeMain.test_notice_send(_id)
        except requests.exceptions.SSLError:
            return ResponseData.fail('请检查系统代理，并设置为关闭在进行测试')
        else:
            return ResponseData.success('通知发送成功')

    @action(methods=['get'], detail=False)
    def get_notice_type(self, request: Request):
        return ResponseData.success('获取通知类型成功', enum_list(NoticeEnum))

    @action(methods=['put'], detail=False)
    def put_status(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """
        obj = self.model.objects.get(id=request.data.get('id'))
        obj.status = request.data.get('status')
        obj.save()
        return ResponseData.success('修改通知状态成功', )
