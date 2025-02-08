# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-17 21:39
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_api.models import ApiHeaders
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.tools.view.model_crud import ModelCRUD


class ApiHeadersSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiHeaders
        fields = '__all__'


class ApiHeadersSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)

    class Meta:
        model = ApiHeaders
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product')
        return queryset


class ApiHeadersCRUD(ModelCRUD):
    model = ApiHeaders
    queryset = ApiHeaders.objects.all()
    serializer_class = ApiHeadersSerializersC
    serializer = ApiHeadersSerializers


class ApiHeadersViews(ViewSet):
    model = ApiHeaders
    serializer_class = ApiHeadersSerializers
