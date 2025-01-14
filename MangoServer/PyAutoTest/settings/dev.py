# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-07-12 14:13
# @Author : 毛鹏

# ************************ 数据源类型 ************************ #

IS_SQLITE = False  # 是否选用sqlite作为数据源，默认使用mysql

# ************************ Mysql配置 ************************ #
MYSQL_PORT = 3306
MYSQL_DB_NAME = 'mango_server'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'mP123456&'
MYSQL_IP = '127.0.0.1'

# ************************ DEBUG配置 ************************ #
DEBUG = False

# ************************ REDIS配置 ************************ #

REDIS = False
# ************************ Minio配置 ************************ #
IS_MINIO = True
MINIO_IP = '127.0.0.1'
MINIO_PORT = 9000


# ************************ 是否允许删除 ************************ #
IS_DELETE = True

# settings.py

# 使用 django-storages 的 S3 后端
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# MinIO 配置
AWS_ACCESS_KEY_ID = 'kGio1ain4dleEQwymPl5'  # MinIO 的 Access Key
AWS_SECRET_ACCESS_KEY = 'lc5YVRRl3ShbPKzDgCPGQnJjxKpKnmEuW2tz9scq'  # MinIO 的 Secret Key
AWS_STORAGE_BUCKET_NAME = 'mango'  # MinIO 存储桶名称
AWS_S3_ENDPOINT_URL = 'http://127.0.0.1:9000'  # MinIO 服务器的地址
AWS_S3_USE_SSL = False  # 如果 MinIO 使用 HTTP 而不是 HTTPS，设置为 False
AWS_S3_FILE_OVERWRITE = True  # 如果不想覆盖同名文件，设置为 False

# **************** 个人配置，开源用户忽略这部分代码 **************** #
# file_name = 'PyAutoTest/settings/database.json'
# if os.path.exists(file_name):
#     # 读取数据
#     with open(file_name, 'r') as file:
#         data = json.load(file)
#
#     mysql_port = data.get('mysql_port', mysql_port)
#     mysql_db_name = data.get('mysql_db_name', mysql_db_name)
#     mysql_user = data.get('mysql_user', mysql_user)
#     mysql_password = data.get('mysql_password', mysql_password)
#     mysql_ip = data.get('mysql_ip', mysql_ip)
