# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-07-12 14:13
# @Author : 毛鹏
# ************************ 数据源类型 ************************ #

IS_SQLITE = False  # 是否选用sqlite作为数据源，默认使用mysql

# ************************ Mysql配置 ************************ #

MYSQL_DB_NAME = 'mango_server'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'mP123456&'
MYSQL_IP = 'db'
MYSQL_PORT = 3306

# ************************ DEBUG配置 ************************ #
DEBUG = False  # 这里也控制了是否使用minio。如果到生产环境，请将DEBUG改为False，False将使用minio

# ************************ REDIS配置 ************************ #

REDIS = False
# ************************ Minio配置 ************************ #
MINIO_STORAGE_ENDPOINT = 'minio:9000'  # 访问IP+端口
MINIO_STORAGE_ACCESS_KEY = 'R3SrN5q9XGWj1n28wpG9'  # ACCESS_KEY
MINIO_STORAGE_SECRET_KEY = 'LliOFBMjp19jFTUw3byUGxgaj6GnmUdsEpRyFjw4'  # SECRET_KEY
MINIO_STORAGE_USE_HTTPS = False  # 如果使用 HTTPS，设置为 True
MINIO_STORAGE_MEDIA_BUCKET_NAME = 'mango-file'  # 桶名称
MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = True  # 桶不存在时自动创建

# ************************ 是否允许删除 ************************ #
IS_DELETE = True
