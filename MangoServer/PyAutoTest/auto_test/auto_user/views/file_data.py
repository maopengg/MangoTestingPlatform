# -*- coding: utf-8 -*-
# @FileData: auto_test
# @Description: 
# @Time   : 2024-05-17 12:32
# @Author : 毛鹏
import json

from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_user.models import FileData, ProjectProduct
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.tools.decorator.error_response import error_response
from PyAutoTest.tools.log_collector import log
from PyAutoTest.tools.view import *
from PyAutoTest.tools.view.model_crud import ModelCRUD


class FileDataSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = FileData
        fields = '__all__'


class FileDataSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project = ProjectSerializers(read_only=True)

    class Meta:
        model = FileData
        fields = '__all__'  # 全部进行序列化

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project',
        )
        return queryset


class FileDataCRUD(ModelCRUD):
    model = FileData
    queryset = FileData.objects.all()
    serializer_class = FileDataSerializersC
    serializer = FileDataSerializers

    @error_response('user')
    def post(self, request: Request):
        project_id = request.data.get('project')
        if project_id is None:
            project_product_id = request.data.get('project_product_id')
            try:
                project_id = ProjectProduct.objects.get(id=project_product_id).project_id
            except ProjectProduct.DoesNotExist:
                return ResponseData.fail(RESPONSE_MSG_0028, )
            data = request.data
            data['project'] = project_id
        else:
            data = request.data
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            self.asynchronous_callback(request)
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
        else:
            log.system.error(f'执行保存时报错，请检查！数据：{request.data}, 报错信息：{json.dumps(serializer.errors)}')
            return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)


class FileDataViews(ViewSet):
    model = FileData
    serializer_class = FileDataSerializers
