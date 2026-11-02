# -*- coding: utf-8 -*-
"""默认部署环境配置。"""

# ── 1. MySQL 数据库 · 必填 ────────────────────────────────────
from urllib.parse import urlsplit
import os

MYSQL_DB_NAME = 'mango_server'
MYSQL_USER = 'root'
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_IP = 'db'
MYSQL_PORT = 3306

# ── 2. 调试与日志 ─────────────────────────────────────────────
DEBUG = False
IS_DEBUG_LOG = False


# ── 3. MCP 访问白名单 ─────────────────────────────────────────
_public_url = os.getenv('PUBLIC_URL', 'http://localhost:8000').rstrip('/')
MCP_ALLOWED_HOSTS = ['localhost:*', '127.0.0.1:*', '[::1]:*', urlsplit(_public_url).netloc]
MCP_ALLOWED_ORIGINS = ['http://localhost:*', 'http://127.0.0.1:*', _public_url]

# ── 4. 文件存储 · 按类型填写 ──────────────────────────────────
# 先选择上传文件、截图和测试结果文件保存到哪里：
# local：保存在运行后端的电脑或服务器上，默认目录为 MangoServer/runtime/media。
#        选择 local 后，下面的 MINIO_* 和 MINIO_PUBLIC_BASE_URL 都不用填。
# minio：保存在 MinIO 文件服务中。
#        必填：MinIO 服务地址、Access Key、Secret Key、桶名（存储空间名称）。
# tos：保存在火山云 TOS 对象存储中。
#      必填：TOS 的 S3 兼容服务地址、Access Key、Secret Key、桶名（存储空间名称）。
FILE_STORAGE_BACKEND = os.getenv('FILE_STORAGE_BACKEND', 'local')
MINIO_STORAGE_REGION = None
MINIO_STORAGE_ENDPOINT = 'minio:9000'
MINIO_STORAGE_ACCESS_KEY = os.getenv('MINIO_STORAGE_ACCESS_KEY', '')
MINIO_STORAGE_SECRET_KEY = os.getenv('MINIO_STORAGE_SECRET_KEY', '')
MINIO_STORAGE_MEDIA_BUCKET_NAME = 'mango-file'
MINIO_PUBLIC_BASE_URL = '/minio/mango-file'
