# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import Database
from PyAutoTest.auto_test.auto_system.views.test_object import TestObjectSerializers
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD, ModelQuery


class DatabaseSerializers(serializers.ModelSerializer):
    class Meta:
        model = Database
        fields = '__all__'


class DatabaseSerializersC(serializers.ModelSerializer):
    project = ProjectSerializers(read_only=True)
    test_obj = TestObjectSerializers(read_only=True)

    class Meta:
        model = Database
        fields = '__all__'


class DatabaseCRUD(ModelCRUD):
    model = Database
    queryset = Database.objects.all()
    serializer_class = DatabaseSerializersC
    serializer = DatabaseSerializers


class DatabaseQuery(ModelQuery):
    model = Database
    serializer_class = DatabaseSerializersC


class DatabaseViews(ViewSet):
    model = Database
    serializer_class = DatabaseSerializers

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
        return ResponseData.success('修改数据库状态成功')
