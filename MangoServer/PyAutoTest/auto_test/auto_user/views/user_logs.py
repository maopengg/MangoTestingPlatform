# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏

from rest_framework import serializers

from PyAutoTest.auto_test.auto_user.models import UserLogs
from PyAutoTest.tools.view.model_crud import ModelCRUD


class UserLogsSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UserLogs
        fields = '__all__'


class UserLogsSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UserLogs
        fields = '__all__'


class UserLogsCRUD(ModelCRUD):
    model = UserLogs
    queryset = UserLogs.objects.all()
    serializer_class = UserLogsSerializers
    serializer = UserLogsSerializers
