# -*- coding: utf-8 -*-
# @FileData: auto_test
# @Description: 
# @Time   : 2024-05-17 12:32
# @Author : 毛鹏
import json
import socket
from typing import Optional

import minio
import urllib3
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.system.models import FileData
from src.apps.system.service.save_minio import SaveMinio
from src.apps.system.views.project_product import ProjectProductSerializersC
from src.common.tools.storage import build_public_file_url
from src.settings import OBJECT_STORAGE_ENABLED
from src.common.tools.decorator.error_response import error_response
from src.common.tools.log_collector import log
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class FileDataSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    test_file = serializers.FileField(use_url=False, allow_null=True, required=False, allow_empty_file=True)
    failed_screenshot = serializers.ImageField(use_url=False, allow_null=True, required=False)
    file_size_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FileData
        fields = '__all__'

    @staticmethod
    def get_file_size_display(obj):
        return format_file_size(obj.file_size or get_storage_file_size(obj))


class FileDataSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    user = serializers.SerializerMethodField(read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    test_file = serializers.FileField(use_url=False, allow_null=True, required=False, allow_empty_file=True)
    failed_screenshot = serializers.ImageField(use_url=False, allow_null=True, required=False)
    file_size_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FileData
        fields = '__all__'  # 全部进行序列化

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('project_product', 'project_product__project', 'user').order_by('-id')

    @staticmethod
    def get_file_size_display(obj):
        return format_file_size(obj.file_size or get_storage_file_size(obj))

    @staticmethod
    def get_user(obj):
        if not obj.user_id:
            return None
        return {
            'id': obj.user_id,
            'name': getattr(obj.user, 'name', ''),
            'username': getattr(obj.user, 'username', ''),
        }


def get_storage_file_size(file_data: FileData) -> int:
    try:
        return file_data.test_file.size if file_data.test_file else 0
    except Exception:
        return 0


def format_file_size(size: Optional[int]) -> str:
    size = int(size or 0)
    if size <= 0:
        return '-'
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f'{value:.1f} {unit}' if unit != 'B' else f'{int(value)} {unit}'
        value /= 1024


def can_download_file(file_data: FileData, request: Request) -> bool:
    if file_data.allow_download:
        return True
    user = getattr(request, 'user', None) or {}
    user_id = user.get('id')
    return bool(user_id and file_data.user_id == user_id)


class FileDataCRUD(ModelCRUD):
    model = FileData
    queryset = FileData.objects.all()
    serializer_class = FileDataSerializersC
    serializer = FileDataSerializers

    @error_response('system')
    def post(self, request: Request):
        if request.data.get('screenshot', False) and OBJECT_STORAGE_ENABLED:
            uploaded_file = request.FILES.get('failed_screenshot')
            if not uploaded_file:
                return ResponseData.fail(RESPONSE_MSG_0030, )
            return ResponseData.success(RESPONSE_MSG_0002, SaveMinio().main(uploaded_file))
        else:
            try:
                if self.model.objects.filter(name=request.data.get('name')):
                    return ResponseData.fail(RESPONSE_MSG_0022)
                data = request.data.copy()
                uploaded_file = request.FILES.get('test_file')
                if uploaded_file:
                    data['file_size'] = uploaded_file.size
                if getattr(request, 'user', None) and request.user.get('id'):
                    data['user'] = request.user.get('id')
                serializer = self.serializer(data=data)
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
                    minio.error.S3Error) as error:
                log.system.error(f'文件上传到MinIO失败，请检查对象存储配置：{error}')
                return ResponseData.fail(RESPONSE_MSG_0026)


class FileDataViews(ViewSet):
    model = FileData
    serializer_class = FileDataSerializers

    @error_response('system')
    @action(methods=['GET'], detail=False)
    def download_url(self, request: Request):
        file_id = request.query_params.get('id')
        if not file_id:
            return ResponseData.fail(RESPONSE_MSG_0029)
        try:
            file_data = FileData.objects.get(id=file_id)
            if not file_data.test_file:
                return ResponseData.fail(RESPONSE_MSG_0030)
            if not can_download_file(file_data, request):
                return ResponseData.fail(RESPONSE_MSG_0030_1)
            return ResponseData.success(RESPONSE_MSG_0001, build_public_file_url(file_data.test_file.name))
        except FileData.DoesNotExist:
            return ResponseData.fail(RESPONSE_MSG_0029)
        except (
                urllib3.exceptions.MaxRetryError, socket.gaierror, urllib3.exceptions.NameResolutionError,
                minio.error.S3Error) as error:
            log.system.error(f'生成MinIO下载地址失败，请检查对象存储配置：{error}')
            return ResponseData.fail(RESPONSE_MSG_0026)

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
