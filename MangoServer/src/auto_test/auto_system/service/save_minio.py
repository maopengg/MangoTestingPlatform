# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-10-30 14:02
# @Author : 毛鹏
import os
import tempfile

from minio import Minio
from minio.commonconfig import ENABLED
from minio.commonconfig import Filter
from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration

from src.exceptions import MangoServerError, ERROR_MSG_0004
from src.settings import IS_MINIO

if IS_MINIO:
    from src.settings import MINIO_STORAGE_ENDPOINT, MINIO_STORAGE_ACCESS_KEY, \
        MINIO_STORAGE_SECRET_KEY, MINIO_STORAGE_MEDIA_BUCKET_NAME


class SaveMinio:
    _lifecycle_set = False  # 类变量，跟踪是否已设置生命周期规则

    def __init__(self, directory_name="screenshot"):
        self.client = Minio(
            MINIO_STORAGE_ENDPOINT,
            access_key=MINIO_STORAGE_ACCESS_KEY,
            secret_key=MINIO_STORAGE_SECRET_KEY,
            secure=False
        )

        self.directory_name = directory_name
        self.lifecycle_config = LifecycleConfig(
            [
                Rule(
                    ENABLED,
                    rule_filter=Filter(prefix=f"{directory_name}/"),
                    rule_id=f"delete-{directory_name}-rule",
                    expiration=Expiration(days=30)
                )
            ]
        )

    def main(self, uploaded_file):
        # 获取文件名
        filename = uploaded_file.name
        object_name = f"{self.directory_name}/{filename}"

        # 创建临时文件来保存上传的文件内容
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            for chunk in uploaded_file.chunks():
                tmp_file.write(chunk)
            temp_file_path = tmp_file.name
        try:
            # 只在第一次调用时设置生命周期规则
            if not SaveMinio._lifecycle_set:
                self.client.set_bucket_lifecycle(MINIO_STORAGE_MEDIA_BUCKET_NAME, self.lifecycle_config)
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
            raise MangoServerError(*ERROR_MSG_0004)