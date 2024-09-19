# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-05-16 17:19
# @Author : 毛鹏
import os
from io import BytesIO

from django.core.files.uploadedfile import InMemoryUploadedFile
from minio import Minio
from minio.error import S3Error
from urllib3.exceptions import MaxRetryError

from PyAutoTest.exceptions.tools_exception import MiniIoConnError, MiniIoFileError
from PyAutoTest.exceptions.error_msg import ERROR_MSG_0042, ERROR_MSG_0043, ERROR_MSG_0044, ERROR_MSG_0045


class MiniIo:

    def __init__(self):
        # 实例化
        try:
            self.client = Minio(
                endpoint="127.0.0.1:9005",
                access_key="minioadmin",
                secret_key="minioadmin",
                secure=False
            )

        except S3Error:
            raise MiniIoConnError(*ERROR_MSG_0042)
        except (MaxRetryError, ValueError):
            raise MiniIoConnError(*ERROR_MSG_0043)

    def file_path_write(self, bucket_name: str, file_name: str, file_path: str) -> str:
        if not self.client.bucket_exists(bucket_name):
            raise MiniIoConnError(*ERROR_MSG_0044)
        try:
            with open(file_path, "rb") as file_data:
                bytes_length = os.path.getsize(file_path)
                self.client.put_object(bucket_name, file_name, file_data, bytes_length)

                return self.client.presigned_get_object(bucket_name, file_name)
        except FileNotFoundError:
            raise MiniIoFileError(*ERROR_MSG_0045)

    def file_object_write(self, bucket_name: str, file_name: str, file_object: InMemoryUploadedFile):
        file_data = BytesIO(file_object.read())
        bytes_length = len(file_data.getvalue())
        self.client.put_object(bucket_name, file_name, file_data, bytes_length)
        return self.client.presigned_get_object(bucket_name, file_name)

    def bucket_all_file(self, bucket_name: str | None = None) -> list[dict]:
        file_name_list = []
        if bucket_name:
            # 获取指定桶中的文件列表
            objects = self.client.list_objects(bucket_name)
            for file in objects:
                file_name_list.append(
                    {'file_name': file.object_name,
                     'file_url': self.client.presigned_get_object(bucket_name, file.object_name)}
                )
        else:
            # 获取所有桶中的文件列表
            buckets = self.client.list_buckets()
            for bucket in buckets:
                objects = self.client.list_objects(bucket.name)
                for file in objects:
                    file_name_list.append(
                        {'file_name': file.object_name,
                         'file_url': self.client.presigned_get_object(bucket.name, file.object_name)}
                    )

        return file_name_list

    def new_bucket(self, bucket_name: str):
        # 新建文件桶
        self.client.make_bucket(bucket_name)
        if not self.client.bucket_exists(bucket_name):
            raise MiniIoConnError(*ERROR_MSG_0044)

    def delete_bucket(self, bucket_name: str):
        # 删除文件桶
        self.client.remove_bucket(bucket_name)
        if self.client.bucket_exists(bucket_name):
            raise MiniIoConnError(*ERROR_MSG_0044)


if __name__ == '__main__':
    object_name1 = '微信收款码-测试.jpg'
    file_path1 = r"C:\Users\Administrator\Desktop\微信收款码1.jpg"
    # print(MiniIo())
    for i in MiniIo().bucket_all_file('text.txt'):
        print(i.get('file_name'))
        print(i.get('file_url'))
