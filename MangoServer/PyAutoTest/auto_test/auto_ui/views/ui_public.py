# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-03-25 18:53
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import UiPublic
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD, ModelQuery


class UiPublicSerializers(serializers.ModelSerializer):
    class Meta:
        model = UiPublic
        fields = '__all__'


class UiPublicSerializersC(serializers.ModelSerializer):
    project = ProjectSerializers(read_only=True)

    class Meta:
        model = UiPublic
        fields = '__all__'


class UiPublicCRUD(ModelCRUD):
    model = UiPublic
    queryset = UiPublic.objects.select_related('project').all()
    serializer_class = UiPublicSerializersC
    serializer = UiPublicSerializers


class UiPublicQuery(ModelQuery):
    """
    条件查
    """
    model = UiPublic
    serializer_class = UiPublicSerializersC


class UiPublicViews(ViewSet):
    model = UiPublic
    serializer_class = UiPublicSerializers

    @action(methods=['put'], detail=False)
    def put_state(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """
        obj = self.model.objects.get(id=request.data.get('id'))
        obj.state = request.data.get('state')
        obj.save()
        return ResponseData.success('修改UI参数状态成功', )
