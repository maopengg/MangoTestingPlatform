import time
import uuid
from datetime import datetime
import os

from minio import Minio
from minio.commonconfig import ENABLED
from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration
from minio.commonconfig import Filter


def upload_to_screenshot_directory(local_file_path):
    """
    上传截图到MinIO，并配置1天后自动删除
    
    Args:
        local_file_path: 本地文件路径
        
    Returns:
        str: 上传后的文件路径
    """
    s = time.time()
    client = Minio(
        "172.16.100.47:9000",
        access_key="admin",
        secret_key="mP123456",
        secure=False
    )

    bucket_name = "mango-file"
    directory_name = "screenshot"

    # 使用传入文件的文件名作为上传文件名
    filename = os.path.basename(local_file_path)
    object_name = f"{directory_name}/{filename}"

    # 设置生命周期规则，使带有"screenshot/"前缀的对象在创建1天后过期
    lifecycle_config = LifecycleConfig(
        [
            Rule(
                ENABLED,
                rule_filter=Filter(prefix="screenshot/"),
                rule_id="delete-screenshot-rule",
                expiration=Expiration(days=1)  # 1天后过期
            )
        ]
    )
    print(time.time() - s)
    # 应用生命周期配置到存储桶
    client.set_bucket_lifecycle(bucket_name, lifecycle_config)

    # 上传文件
    client.fput_object(
        bucket_name,
        object_name,
        local_file_path
    )

    return f'{bucket_name}/{object_name}'


# 使用示例
local_file_path = r"D:\code\MangoTestingPlatform\MangoServer\mango-file\failed_screenshot\创建历史1747217994000.jpg"
result = upload_to_screenshot_directory(local_file_path)
print(f"上传结果: {result}")
