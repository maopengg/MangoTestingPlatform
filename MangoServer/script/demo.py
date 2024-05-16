# 从minio库中导入Minio客户端类
import os

from minio import Minio

# 实例化
client = Minio(
    # endpoint指定的是你Minio的远程IP及端口
    endpoint="127.0.0.1:9005",
    # accesskey指定的是你的Minio服务器访问key
    # 默认值为minioadmin
    access_key="minioadmin",
    # secret_key指定的是你登录时需要用的key，类似密码
    # 默认值也是minioadmin
    secret_key="minioadmin",
    # secure指定是否以安全模式创建Minio连接
    # 建议为False
    secure=False
)
bucket_name = "test"
object_name = '微信收款码.jpg'
file_path = r"C:\Users\Administrator\Desktop\微信收款码.jpg"
if client.bucket_exists(bucket_name):
    with open(file_path, "rb") as file_data:
        bytes_length = os.path.getsize(file_path)
        client.put_object(bucket_name, object_name, file_data, bytes_length)

        url = client.presigned_get_object(bucket_name, object_name)
        print(url)
else:
    print(1)