# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-10-30 14:02
# @Author : 毛鹏
import os
import posixpath
import tempfile

from minio import Minio
from minio.commonconfig import ENABLED
from minio.commonconfig import Filter
from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration

from src.common.exceptions import MangoServerError, ERROR_MSG_0004
from src.settings import IS_MINIO
from src.common.tools.log_collector import log

if IS_MINIO:
    from src.settings import MINIO_STORAGE_ENDPOINT, MINIO_STORAGE_ACCESS_KEY, \
        MINIO_STORAGE_SECRET_KEY, MINIO_STORAGE_MEDIA_BUCKET_NAME, MINIO_STORAGE_USE_HTTPS
    from django.conf import settings


class SaveMinio:
    _lifecycle_set = False  # 类变量，跟踪是否已设置生命周期规则

    def __init__(self, directory_name="screenshot"):
        self.client = Minio(
            MINIO_STORAGE_ENDPOINT,
            access_key=MINIO_STORAGE_ACCESS_KEY,
            secret_key=MINIO_STORAGE_SECRET_KEY,
            secure=MINIO_STORAGE_USE_HTTPS
        )
        if getattr(settings, 'MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE', False):
            self.client._base_url.virtual_style_flag = True

        self.location = f"auto_test_report/{os.getenv('DJANGO_ENV', 'master')}".strip('/')
        self.directory_name = directory_name.strip('/')
        self.object_prefix = posixpath.join(self.location, self.directory_name)
        self.lifecycle_config = LifecycleConfig(
            [
                Rule(
                    ENABLED,
                    rule_filter=Filter(prefix=f"{self.object_prefix}/"),
                    rule_id=f"delete-{self.object_prefix.replace('/', '-')}-rule",
                    expiration=Expiration(days=30)
                )
            ]
        )

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
            # 只在第一次调用时设置生命周期规则
            if not SaveMinio._lifecycle_set:
                try:
                    self.client.set_bucket_lifecycle(MINIO_STORAGE_MEDIA_BUCKET_NAME, self.lifecycle_config)
                except Exception as error:
                    log.system.warning(f'MinIO生命周期规则设置失败，已跳过，不影响文件上传：{error}')
                SaveMinio._lifecycle_set = True
            # 上传文件到MinIO
            self.client.fput_object(
                MINIO_STORAGE_MEDIA_BUCKET_NAME,
                object_name,
                temp_file_path
            )
            # 删除临时文件
            os.unlink(temp_file_path)
            return f'{MINIO_STORAGE_MEDIA_BUCKET_NAME}/{object_name}'
        except Exception as e:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            log.system.error(f'MinIO文件上传失败，请检查对象存储配置：{e}')
            raise MangoServerError(*ERROR_MSG_0004)
