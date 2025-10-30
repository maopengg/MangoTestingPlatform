# -*- coding: utf-8 -*-
# @FileData: auto_test
# @Description: 
# @Time   : 2024-05-17 12:32
# @Author : 毛鹏
import json
import socket

import minio
import urllib3
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_system.models import FileData
from src.auto_test.auto_system.service.save_minio import SaveMinio
from src.settings import IS_MINIO
from src.tools.decorator.error_response import error_response
from src.tools.log_collector import log
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


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

    @error_response('system')
    def post(self, request: Request):
        if request.data.get('screenshot', False) and IS_MINIO:
            uploaded_file = request.FILES.get('failed_screenshot')
            if not uploaded_file:
                return ResponseData.fail(RESPONSE_MSG_0030, )
            return ResponseData.success(RESPONSE_MSG_0002, SaveMinio().main(uploaded_file))
        else:
            try:
                if self.model.objects.filter(name=request.data.get('name')):
                    return ResponseData.fail(RESPONSE_MSG_0022)
                serializer = self.serializer(data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    return ResponseData.success(RESPONSE_MSG_0002,
                                                request.data.get('file_path', None) or serializer.data)
                else:
                    log.system.error(
                        f'执行保存时报错，请检查！数据：{request.data}, 报错信息：{json.dumps(serializer.errors)}')
                    return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)
            except (
                    urllib3.exceptions.MaxRetryError, socket.gaierror, urllib3.exceptions.NameResolutionError,
                    minio.error.S3Error):
                return ResponseData.fail(RESPONSE_MSG_0026)


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
        uploaded_file = request.FILES.get('file')
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
