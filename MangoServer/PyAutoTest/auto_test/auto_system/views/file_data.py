# -*- coding: utf-8 -*-
# @FileData: auto_test
# @Description: 
# @Time   : 2024-05-17 12:32
# @Author : 毛鹏
import json

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import FileData, ProjectProduct
from PyAutoTest.tools.decorator.error_response import error_response
from PyAutoTest.tools.log_collector import log
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *


class FileDataSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = FileData
        fields = '__all__'


class FileDataSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = FileData
        fields = '__all__'  # 全部进行序列化

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset


class FileDataCRUD(ModelCRUD):
    model = FileData
    queryset = FileData.objects.all()
    serializer_class = FileDataSerializersC
    serializer = FileDataSerializers

    @error_response('user')
    def post(self, request: Request):
        if self.model.objects.filter(name=request.data.get('name')):
            return ResponseData.fail(RESPONSE_MSG_0022)
        serializer = self.serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
        else:
            log.system.error(f'执行保存时报错，请检查！数据：{request.data}, 报错信息：{json.dumps(serializer.errors)}')
            return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)


class FileDataViews(ViewSet):
    model = FileData
    serializer_class = FileDataSerializers

    @error_response('system')
    @action(methods=['POST'], detail=False)
    def post_upload(self, request: Request):
        """
        上传文件
        @param request:
        @return:
        """
        # 获取上传的文件
        uploaded_file = request.FILES.get('file')
        print(uploaded_file)
        project_id = request.data.get('project_id')
        file_type = request.data.get('type')
        file_name = request.data.get('name')
        file_price = request.data.get('price')

        file_data = FileData(
            project_id=project_id,
            type=file_type,
            name=file_name,
            price=file_price,
            file=uploaded_file
        )
        file_data.save()
        return ResponseData.success(RESPONSE_MSG_0031, self.serializer_class(file_data).data)
