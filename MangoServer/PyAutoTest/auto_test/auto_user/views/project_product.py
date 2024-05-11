# -*- coding: utf-8 -*-
# @ProjectProduct: MangoServer
# @Description: 项目表
# @Time   : 2023-03-03 12:21
# @Author : 毛鹏
import logging

from rest_framework import serializers

from PyAutoTest.tools.view.model_crud import ModelCRUD
from .project import ProjectSerializers
from ..models import ProjectProduct

log = logging.getLogger('user')


class ProjectProductSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ProjectProduct
        fields = '__all__'


class ProjectProductSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project = ProjectSerializers(read_only=True)

    class Meta:
        model = ProjectProduct
        fields = '__all__'  # 全部进行序列化

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project')
        return queryset


class ProjectProductCRUD(ModelCRUD):
    model = ProjectProduct
    queryset = ProjectProduct.objects.all()
    serializer_class = ProjectProductSerializersC
    serializer = ProjectProductSerializers

    pass
