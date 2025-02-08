# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏

from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_api.models import ApiCaseDetailedParameter
from src.tools.view.model_crud import ModelCRUD


class ApiCaseDetailedParameterSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiCaseDetailedParameter
        fields = '__all__'


class ApiCaseDetailedParameterCRUD(ModelCRUD):
    model = ApiCaseDetailedParameter
    queryset = ApiCaseDetailedParameter.objects.all()
    serializer_class = ApiCaseDetailedParameterSerializers
    serializer = ApiCaseDetailedParameterSerializers


class ApiCaseDetailedParameterViews(ViewSet):
    model = ApiCaseDetailedParameter
    serializer_class = ApiCaseDetailedParameterSerializers
