# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-07-12 14:13
# @Author : 毛鹏
# ************************ 数据源类型 ************************ #

IS_SQLITE = False  # 是否选用sqlite作为数据源，默认使用mysql

# ************************ Mysql配置 ************************ #

MYSQL_DB_NAME = 'test_mango_server'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'mP123456&'
MYSQL_IP = 'db'
MYSQL_PORT = 3306

# ************************ DEBUG配置 ************************ #
# 这里也控制了是否使用minio
# True开启debug就不会使用minio
# 生产环境=True，生产环境=False，使用minio

DEBUG = False
IS_DEBUG_LOG = False

# ************************ REDIS配置 ************************ #

REDIS = False
# ************************ Minio配置 ************************ #
IS_MINIO = True

if IS_MINIO:
    MINIO_STORAGE_ENDPOINT = 'minio:9000'  # 访问IP+端口
    MINIO_STORAGE_USE_HTTPS = False  # 如果使用 HTTPS，设置为 True
    MINIO_STORAGE_MEDIA_BUCKET_NAME = 'mango-file'  # 桶名称
    MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = True  # 桶不存在时自动创建
    MINIO_STORAGE_ACCESS_KEY = 'jkPxfhklQqhUmDEpP0po'  # ACCESS_KEY
    MINIO_STORAGE_SECRET_KEY = 'aQriZMcIH8rVXc5uNpondikDNOLdPbsba77dT6mF'  # SECRET_KEY
    # MINIO_STORAGE_ACCESS_KEY = 'eQUpBpIGUgHc1f2nZbte'  # 家里的
    # MINIO_STORAGE_SECRET_KEY = 'AqNnxHTrxVAZtPUgu6lLEArekqjHfMtku4tM1qgz'  # 家里的
# ************************ 是否允许删除 ************************ #
IS_DELETE = True
# *************** 是否发送error日志协助芒果修复问题 *************** #
IS_SEND_MAIL = True
