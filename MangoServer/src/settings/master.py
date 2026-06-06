# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-07-12 14:13
# @Author : 毛鹏
# ************************ 数据库配置 ************************ #
# master 是默认部署环境，开源 docker-compose 默认使用该环境。
# IS_SQLITE=True 时使用 MangoServer/db.sqlite3；IS_SQLITE=False 时使用下面的 MySQL。
IS_SQLITE = False

# MySQL 连接信息：docker-compose 会通过 .env 注入数据库容器；如果不使用容器，请改为自己的数据库地址。
MYSQL_DB_NAME = 'mango_server'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'mP123456&'
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
MCP_ALLOWED_HOSTS = ['43.142.161.61:8000']
MCP_ALLOWED_ORIGINS = ['http://43.142.161.61:8000']

# ************************ 文件存储配置 ************************ #
# FILE_STORAGE_BACKEND 支持 local/minio/tos。
# master 默认使用 MinIO，适合 docker-compose 开源 demo。
# MINIO_STORAGE_ENDPOINT 是后端容器内部访问地址，不要返回给前端。
# MINIO_PUBLIC_BASE_URL 是前端下载地址前缀，demo 中通过 nginx /minio 转发到 MinIO。
FILE_STORAGE_BACKEND = 'minio'
MINIO_STORAGE_ENDPOINT = 'minio:9000'
MINIO_STORAGE_ACCESS_KEY = 'admin'
MINIO_STORAGE_SECRET_KEY = 'mP123456'
MINIO_STORAGE_USE_HTTPS = False
MINIO_STORAGE_MEDIA_BUCKET_NAME = 'mango-file'
MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = True
MINIO_PUBLIC_BASE_URL = '/minio/mango-file'

# ************************ 是否允许删除 ************************ #
# IS_DELETE=False 表示演示环境限制删除/新增/修改；IS_DELETE=True 表示按正常权限执行。
IS_DELETE = True

# ************************ 错误日志上报 ************************ #
# 开源用户没有邮件配置时建议设为 False。
IS_SEND_MAIL = True
