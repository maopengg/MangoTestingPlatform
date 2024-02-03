# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.auto_test.auto_system.service.get_database import GetDataBase
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.auto_test.auto_user.views.user import UserSerializers
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD
from PyAutoTest.tools.view_utils.response_data import ResponseData
from PyAutoTest.tools.view_utils.response_msg import *


class TestObjectSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = TestObject
        fields = '__all__'


class TestObjectSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project = ProjectSerializers(read_only=True)
    executor_name = UserSerializers(read_only=True)

    class Meta:
        model = TestObject
        fields = '__all__'


class TestObjectCRUD(ModelCRUD):
    model = TestObject
    queryset = TestObject.objects.all()
    serializer_class = TestObjectSerializersC
    serializer = TestObjectSerializers


class TestObjectViews(ViewSet):
    model = TestObject
    serializer_class = TestObjectSerializers

    @action(methods=['get'], detail=False)
    def get_test_obj_name(self, request: Request):
        """
         获取平台枚举
         :param request:
         :return:
         """
        res = TestObject.objects.values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success(RESPONSE_MSG_0095, data)

    @action(methods=['put'], detail=False)
    def put_status(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """
        db_status = request.data.get('db_status')
        try:
            obj = self.model.objects.get(id=request.data.get('id'))
            if db_status:
                GetDataBase.get_mysql_config(obj.id)
            obj.db_status = db_status
            obj.save()
            return ResponseData.success(RESPONSE_MSG_0096)
        except MangoServerError as error:
            return ResponseData.fail((error.code, error.msg))
