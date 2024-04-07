# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-11-13 10:42
# @Author : 毛鹏
import logging

from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiInfoDetails
from PyAutoTest.auto_test.auto_api.views.api_info import ApiInfoSerializers
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD

log = logging.getLogger('api')


class ApiInfoDetailsSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiInfoDetails
        fields = '__all__'


class ApiInfoDetailsSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    api_info = ApiInfoSerializers(read_only=True)

    class Meta:
        model = ApiInfoDetails
        fields = '__all__'


class ApiInfoDetailsCRUD(ModelCRUD):
    model = ApiInfoDetails
    queryset = ApiInfoDetails.objects.all()
    serializer_class = ApiInfoDetailsSerializersC
    serializer = ApiInfoDetailsSerializers


class ApiInfoDetailsViews(ViewSet):
    model = ApiInfoDetails
    serializer_class = ApiInfoDetailsSerializers
