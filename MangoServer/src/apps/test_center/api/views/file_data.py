# -*- coding: utf-8 -*-
# @FileData: auto_test
# @Description:
# @Time   : 2024-05-17 12:32
# @Author : 毛鹏
import json
import socket

import minio
import urllib3
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.test_center.api.serializers.file_data import FileDataSerializersC
from src.apps.test_center.api.serializers.file_data_mutation import FileDataSerializers
from src.apps.test_center.models import FileData
from src.apps.test_center.services.storage.execution_artifact import ExecutionArtifactService
from src.common.decorators.error_response import error_response
from src.common.logging import log
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0003,
    RESPONSE_MSG_0022,
    RESPONSE_MSG_0026,
    RESPONSE_MSG_0029,
    RESPONSE_MSG_0030,
    RESPONSE_MSG_0030_1,
    RESPONSE_MSG_0031,
    RESPONSE_MSG_0321,
)
from src.common.storage import build_public_file_url


def can_download_file(file_data: FileData, request: Request) -> bool:
    """检查当前用户是否可下载指定测试文件"""
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
    page_permission_key = 'config.test_files'

    @error_response('system')
    def post(self, request: Request):
        """新增测试文件"""
        if request.data.get('screenshot', False):
            file_field = request.data.get('file_field') or 'failed_screenshot'
            file_dir = ExecutionArtifactService.normalize_directory(request.data.get('file_dir') or '')
            uploaded_file = request.FILES.get(file_field) or request.FILES.get('failed_screenshot')
            if not uploaded_file:
                return ResponseData.fail(RESPONSE_MSG_0030, )
            if file_dir == ExecutionArtifactService.PERF_CAPTURE_DIRECTORY and uploaded_file.size > 100_000_000:
                return ResponseData.fail(RESPONSE_MSG_0321)
            return ResponseData.success(RESPONSE_MSG_0002,
                                        ExecutionArtifactService.save_upload(uploaded_file, file_dir))
        else:
            try:
                if self.model.objects.filter(name=request.data.get('name')):
                    return ResponseData.fail(RESPONSE_MSG_0022)
                data = request.data.copy()
                data['type'] = 0
                uploaded_file = request.FILES.get('test_file')
                if uploaded_file:
                    data['file_size'] = uploaded_file.size
                if getattr(request, 'user', None) and request.user.get('id'):
                    data['user'] = request.user.get('id')
                    data['update_user'] = request.user.get('id')
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
        """获取测试文件下载地址"""
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
    @action(methods=['GET'], detail=False)
    def artifact_download_url(self, request: Request):
        """获取报告附件下载地址"""
        try:
            normalized = ExecutionArtifactService.normalize_path(request.query_params.get('path'))
            if f'/{ExecutionArtifactService.PERF_CAPTURE_DIRECTORY}/' in f'/{normalized}':
                return ResponseData.fail(RESPONSE_MSG_0030_1)
            return ResponseData.success(
                RESPONSE_MSG_0001,
                ExecutionArtifactService.public_url(normalized),
            )
        except (TypeError, ValueError):
            return ResponseData.fail(RESPONSE_MSG_0029)
        except (
                urllib3.exceptions.MaxRetryError, socket.gaierror, urllib3.exceptions.NameResolutionError,
                minio.error.S3Error) as error:
            log.system.error(f'生成执行产物访问地址失败，请检查对象存储配置：{error}')
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
