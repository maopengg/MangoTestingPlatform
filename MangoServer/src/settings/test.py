# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-07-12 14:13
# @Author : 毛鹏
# ************************ 数据库配置 ************************ #
# test 是公司测试环境配置，默认连接测试数据库。
# 开源用户如无公司测试环境，可以复制 master.py 的 MinIO 配置，或改成 FILE_STORAGE_BACKEND='local'。
# IS_SQLITE=True 时使用 MangoServer/db.sqlite3；IS_SQLITE=False 时使用下面的 MySQL。
IS_SQLITE = False

# MySQL 连接信息：请替换为自己的测试数据库。
MYSQL_DB_NAME = 'test_mango_server'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'mP123456&'
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
# MCP 有 Host/Origin 安全校验。test 当前默认允许公司测试域名。
# 如果部署到自己的域名/IP，需要同步修改 HOSTS 与 ORIGINS。
MCP_ALLOWED_HOSTS = ['127.0.0.1:*', 'localhost:*', '[::1]:*']
MCP_ALLOWED_ORIGINS = ['http://127.0.0.1:*', 'http://localhost:*', 'http://[::1]:*']

# ************************ 文件存储配置 ************************ #
# FILE_STORAGE_BACKEND 支持 local/minio/tos。
# test 默认使用火山 TOS。TOS 使用 S3 兼容协议，因此仍沿用 MINIO_STORAGE_* 变量名。
# MINIO_STORAGE_ENDPOINT 是后端访问 TOS 的 S3 endpoint。
# MINIO_PUBLIC_BASE_URL 是前端下载地址前缀，应配置成浏览器可访问的桶域名或 CDN 域名。
FILE_STORAGE_BACKEND = 'tos'
MINIO_STORAGE_ENDPOINT = 'tos-s3-cn-beijing.volces.com'  # 访问IP+端口
MINIO_STORAGE_ACCESS_KEY = 'AKLTNmI0ZDYzZDUzYTYyNGE4Nzk3OGNjNjA2MDI5NDRlZTA'  # ACCESS_KEY
MINIO_STORAGE_SECRET_KEY = 'TVdNMFpqZzJZalV4TWpRMU5HVTRZbUkwTjJFellqazJORGhqWlRZeU56TQ=='  # SECRET_KEY
MINIO_STORAGE_USE_HTTPS = True  # 如果使用 HTTPS，设置为 True
MINIO_STORAGE_MEDIA_BUCKET_NAME = 'regression-report'  # 桶名称
MINIO_STORAGE_MEDIA_USE_PRESIGNED = True  # 私有桶下载时返回临时签名URL
MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = False  # 桶不存在时自动创建
MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS = True  # 云厂商受限AK可能不允许检查桶是否存在，直接按已存在处理
MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE = True  # 火山TOS S3兼容接口需要 bucket.endpoint/object 访问风格
MINIO_PUBLIC_BASE_URL = 'https://regression-report.tos-s3-cn-beijing.volces.com'

# ************************ 是否允许删除 ************************ #
# IS_DELETE=False 表示演示环境限制删除/新增/修改；IS_DELETE=True 表示按正常权限执行。
IS_DELETE = True

# ************************ 错误日志上报 ************************ #
# 开源用户没有邮件配置时建议设为 False。
IS_SEND_MAIL = True
