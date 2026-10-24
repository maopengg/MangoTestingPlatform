# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-07-12 14:13
# @Author : 毛鹏
import os

# ************************ 数据库配置 ************************ #
# test 是开源测试环境配置，默认连接测试数据库并使用 MinIO。
# 对象存储参数可通过环境变量覆盖；无需对象存储时设置 FILE_STORAGE_BACKEND='local'。
# IS_SQLITE=True 时使用 MangoServer/db.sqlite3；IS_SQLITE=False 时使用下面的 MySQL。
IS_SQLITE = False

# MySQL 连接信息：请替换为自己的测试数据库。
MYSQL_DB_NAME = 'test_mango_server'
MYSQL_USER = 'root'
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_IP = 'db'
MYSQL_PORT = 3306

# ************************ 调试与日志 ************************ #
# 测试/公网环境建议保持 DEBUG=False。
DEBUG = False
# IS_DEBUG_LOG 控制业务日志是否输出 debug 级别。
IS_DEBUG_LOG = False


# ************************ Redis配置 ************************ #
# 当前项目默认不依赖 Redis。
REDIS = False

# ************************ MCP配置 ************************ #
# MCP 有 Host/Origin 安全校验。请按实际部署配置允许访问的域名或本机地址。
# 如果部署到自己的域名/IP，需要同步修改 HOSTS 与 ORIGINS。
MCP_ALLOWED_HOSTS = ['127.0.0.1:*', 'localhost:*', '[::1]:*']
MCP_ALLOWED_ORIGINS = ['http://127.0.0.1:*', 'http://localhost:*', 'http://[::1]:*']

# ************************ 文件存储配置 ************************ #
# 对象存储凭据不内置；使用 MinIO/TOS 时请设置 MINIO_STORAGE_ACCESS_KEY 和 MINIO_STORAGE_SECRET_KEY。
# FILE_STORAGE_BACKEND 支持 local/minio/tos。
# MinIO 和 TOS 均使用 S3 兼容协议，服务地址和凭据通过部署环境配置。
# MINIO_STORAGE_ENDPOINT 是后端使用的 S3 兼容服务地址。
# MINIO_PUBLIC_BASE_URL 是前端下载地址前缀，应配置成浏览器可访问的桶域名或 CDN 域名。
FILE_STORAGE_BACKEND = os.getenv('FILE_STORAGE_BACKEND', 'minio')
MINIO_STORAGE_ENDPOINT = os.getenv('MINIO_STORAGE_ENDPOINT', 'minio:9000')
MINIO_STORAGE_ACCESS_KEY = os.getenv('MINIO_STORAGE_ACCESS_KEY', '')
MINIO_STORAGE_SECRET_KEY = os.getenv('MINIO_STORAGE_SECRET_KEY', '')
MINIO_STORAGE_USE_HTTPS = os.getenv('MINIO_STORAGE_USE_HTTPS', 'false').lower() in {'1', 'true', 'yes', 'on'}
MINIO_STORAGE_MEDIA_BUCKET_NAME = os.getenv('MINIO_STORAGE_MEDIA_BUCKET_NAME', 'mango-file')
MINIO_STORAGE_MEDIA_USE_PRESIGNED = os.getenv('MINIO_STORAGE_MEDIA_USE_PRESIGNED', 'false').lower() in {'1', 'true', 'yes', 'on'}
MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = os.getenv('MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET', 'true').lower() in {'1', 'true', 'yes', 'on'}
MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS = os.getenv('MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS', 'false').lower() in {'1', 'true', 'yes', 'on'}
MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE = os.getenv('MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE', 'false').lower() in {'1', 'true', 'yes', 'on'}
MINIO_PUBLIC_BASE_URL = os.getenv('MINIO_PUBLIC_BASE_URL', '/minio/mango-file')
