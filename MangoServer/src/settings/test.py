# -*- coding: utf-8 -*-
"""测试环境配置。"""

# ── 1. MySQL 数据库 · 必填 ────────────────────────────────────
import os

MYSQL_DB_NAME = 'test_mango_server'
MYSQL_USER = 'root'
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_IP = 'db'
MYSQL_PORT = 3306

# ── 2. 调试与日志 ─────────────────────────────────────────────
DEBUG = False
IS_DEBUG_LOG = False


# ── 3. MCP 访问白名单 ─────────────────────────────────────────
MCP_ALLOWED_HOSTS = ['127.0.0.1:*', 'localhost:*', '[::1]:*']
MCP_ALLOWED_ORIGINS = ['http://127.0.0.1:*', 'http://localhost:*', 'http://[::1]:*']

# ── 4. 文件存储 · 按类型填写 ──────────────────────────────────
# 先选择上传文件、截图和测试结果文件保存到哪里：
# local：保存在运行后端的电脑或服务器上，默认目录为 MangoServer/runtime/media。
#        选择 local 后，下面的 MINIO_* 和 MINIO_PUBLIC_BASE_URL 都不用填。
# minio：保存在 MinIO 文件服务中。
#        必填：MinIO 服务地址、Access Key、Secret Key、桶名（存储空间名称）。
# tos：保存在火山云 TOS 对象存储中。
#      必填：TOS 的 S3 兼容服务地址、Access Key、Secret Key、桶名（存储空间名称）。
FILE_STORAGE_BACKEND = os.getenv('FILE_STORAGE_BACKEND', 'minio')
MINIO_STORAGE_REGION = None
MINIO_STORAGE_ENDPOINT = os.getenv('MINIO_STORAGE_ENDPOINT', 'minio:9000')
MINIO_STORAGE_ACCESS_KEY = os.getenv('MINIO_STORAGE_ACCESS_KEY', '')
MINIO_STORAGE_SECRET_KEY = os.getenv('MINIO_STORAGE_SECRET_KEY', '')
MINIO_STORAGE_MEDIA_BUCKET_NAME = os.getenv('MINIO_STORAGE_MEDIA_BUCKET_NAME', 'mango-file')
MINIO_PUBLIC_BASE_URL = os.getenv('MINIO_PUBLIC_BASE_URL', '/minio/mango-file')
