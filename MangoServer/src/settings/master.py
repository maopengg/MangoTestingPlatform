# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-07-12 14:13
# @Author : 毛鹏
from urllib.parse import urlsplit
import os

# ************************ 数据库配置 ************************ #
# master 是默认部署环境，开源 docker-compose 默认使用该环境。
# IS_SQLITE=True 时使用 MangoServer/db.sqlite3；IS_SQLITE=False 时使用下面的 MySQL。
IS_SQLITE = False

# MySQL 连接信息：docker-compose 会通过 .env 注入数据库容器；如果不使用容器，请改为自己的数据库地址。
MYSQL_DB_NAME = 'mango_server'
MYSQL_USER = 'root'
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_IP = 'db'
MYSQL_PORT = 3306

# ************************ 调试与日志 ************************ #
# 公网/生产类环境应保持 DEBUG=False。
DEBUG = False
# IS_DEBUG_LOG 控制业务日志是否输出 debug 级别。
IS_DEBUG_LOG = False


# ************************ Redis配置 ************************ #
# 当前项目默认不依赖 Redis。
REDIS = False

# ************************ MCP配置 ************************ #
# MCP 有 Host/Origin 安全校验。master 当前默认允许开源 demo 服务器地址。
# 如果部署到自己的域名/IP，需要同步修改 HOSTS 与 ORIGINS，例如：
#   MCP_ALLOWED_HOSTS = ['auto.example.com']
#   MCP_ALLOWED_ORIGINS = ['https://auto.example.com']
_public_url = os.getenv('PUBLIC_URL', 'http://localhost:8000').rstrip('/')
MCP_ALLOWED_HOSTS = ['localhost:*', '127.0.0.1:*', '[::1]:*', urlsplit(_public_url).netloc]
MCP_ALLOWED_ORIGINS = ['http://localhost:*', 'http://127.0.0.1:*', _public_url]

# ************************ 文件存储配置 ************************ #
# FILE_STORAGE_BACKEND 支持 local/minio/tos。
# MinIO 和 TOS 均使用 S3 兼容协议，服务地址和凭据通过部署环境配置。
# MINIO_STORAGE_ENDPOINT 是后端使用的 S3 兼容服务地址。
# MINIO_PUBLIC_BASE_URL 是前端下载地址前缀，应配置成浏览器可访问的桶域名或 CDN 域名。
FILE_STORAGE_BACKEND = os.getenv('FILE_STORAGE_BACKEND', 'local')
MINIO_STORAGE_ENDPOINT = 'minio:9000'
MINIO_STORAGE_ACCESS_KEY = os.getenv('MINIO_STORAGE_ACCESS_KEY', '')
MINIO_STORAGE_SECRET_KEY = os.getenv('MINIO_STORAGE_SECRET_KEY', '')
MINIO_STORAGE_USE_HTTPS = False
MINIO_STORAGE_MEDIA_BUCKET_NAME = 'mango-file'
MINIO_STORAGE_MEDIA_USE_PRESIGNED = False
MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = True
MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS = False
MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE = False
MINIO_PUBLIC_BASE_URL = '/minio/mango-file'
