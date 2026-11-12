# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2025-10-30 14:02
# @Author : 毛鹏
import os
import posixpath
import tempfile

from django.conf import settings
from minio import Minio
from minio.error import S3Error

from src.apps.test_center.exceptions import TEST_ARTIFACT_SAVE_FAILED, TestCenterError
from src.common.logging import log


class SaveMinio:
    def __init__(self, directory_name="screenshot"):
        self.client = Minio(
            settings.MINIO_STORAGE_ENDPOINT,
            access_key=settings.MINIO_STORAGE_ACCESS_KEY,
            secret_key=settings.MINIO_STORAGE_SECRET_KEY,
            secure=settings.MINIO_STORAGE_USE_HTTPS
        )
        if getattr(settings, 'MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE', False):
            self.client._base_url.virtual_style_flag = True

        # UI 执行产物与主动上传文件、完整执行结果使用同一个对象存储根目录。
        # 环境继续由存储桶隔离，避免同一类文件分散在多套顶层前缀下。
        self.location = str(getattr(settings, 'FILE_STORAGE_ROOT', 'mango-testing-platform/master')).strip('/\\')
        self.directory_name = directory_name.strip('/')
        self.object_prefix = posixpath.join(self.location, self.directory_name)

    @staticmethod
    def _storage_name() -> str:
        backend = str(getattr(settings, 'FILE_STORAGE_BACKEND', 'minio') or 'minio').lower()
        return {'tos': 'TOS', 'minio': 'MinIO'}.get(backend, '对象存储')

    @classmethod
    def failure_reason(cls, error: Exception) -> str:
        """返回可展示的失败分类；原始异常仅记录在服务端日志。"""
        storage_name = cls._storage_name()
        if isinstance(error, S3Error):
            error_code = str(error.code or '')
            if error_code in {'AccessDenied', 'InvalidAccessKeyId', 'SignatureDoesNotMatch', 'InvalidToken'}:
                return f'{storage_name}鉴权失败，请检查访问凭证及存储桶写入权限'
            if error_code in {'NoSuchBucket', 'NoSuchKey'}:
                return f'{storage_name}存储桶不存在或访问路径错误'
            if error_code in {'EntityTooLarge', 'RequestEntityTooLarge'}:
                return f'{storage_name}拒绝上传，文件大小超过限制'
            if error_code in {'RequestTimeout', 'SlowDown', 'ServiceUnavailable', 'InternalError'}:
                return f'{storage_name}服务暂时不可用，请稍后重试'
            return f'{storage_name}拒绝保存文件（错误码：{error_code or "未知"}）'

        error_name = type(error).__name__.lower()
        error_text = str(error).lower()
        if 'timeout' in error_name or 'timed out' in error_text or 'timeout' in error_text:
            return f'连接{storage_name}超时，请检查对象存储网络及服务状态'
        if any(keyword in error_text for keyword in
               ('name or service not known', 'nodename nor servname', 'temporary failure in name resolution')):
            return f'无法解析{storage_name}服务地址，请检查对象存储 Endpoint 或 DNS'
        if any(keyword in error_name for keyword in ('connection', 'connect', 'maxretry')):
            return f'无法连接{storage_name}，请检查对象存储 Endpoint、网络及端口'
        if isinstance(error, PermissionError):
            return f'{storage_name}文件写入权限不足'
        return f'{storage_name}保存文件异常，请管理员查看服务端日志'

    def main(self, uploaded_file):
        # 获取文件名
        filename = uploaded_file.name
        object_name = posixpath.join(self.object_prefix, filename)

        # 创建临时文件来保存上传的文件内容
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            for chunk in uploaded_file.chunks():
                tmp_file.write(chunk)
            temp_file_path = tmp_file.name
        try:
            # 测试文件与执行产物共用存储桶，上传路径不得修改整个桶的生命周期。
            # 截图、视频由每日清理任务按当前环境前缀及保留配置回收。
            # 上传文件到MinIO
            self.client.fput_object(
                settings.MINIO_STORAGE_MEDIA_BUCKET_NAME,
                object_name,
                temp_file_path
            )
            # 删除临时文件
            os.unlink(temp_file_path)
            return f'{settings.MINIO_STORAGE_MEDIA_BUCKET_NAME}/{object_name}'
        except Exception as e:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            log.system.error(f'MinIO文件上传失败，请检查对象存储配置：{e}')
            raise TestCenterError(TEST_ARTIFACT_SAVE_FAILED, value=(self.failure_reason(e),), error=str(e))
