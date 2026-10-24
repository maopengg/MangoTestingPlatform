# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-07-12 14:13
# @Author : 毛鹏
import json
import os

# ************************ 数据库配置 ************************ #
# dev 是本地/开发环境配置。
# 开源用户可以直接改这里，或在 src/settings/database.json 中覆盖下面的 MySQL 配置。
# IS_SQLITE=True 时使用 MangoServer/db.sqlite3；IS_SQLITE=False 时使用下面的 MySQL。
IS_SQLITE = False

# MySQL 连接信息：如果使用 docker-compose，host 通常填 db；如果连接外部数据库，填数据库域名/IP。
MYSQL_PORT = 3306
MYSQL_DB_NAME = 'dev_mango_server'
MYSQL_USER = 'root'
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_IP = '127.0.0.1'

# ************************ 调试与日志 ************************ #
# DEBUG 控制 Django 调试模式；生产/公网环境不要开启。
DEBUG = True
# IS_DEBUG_LOG 控制业务日志是否输出 debug 级别。
IS_DEBUG_LOG = True


# ************************ Redis配置 ************************ #
# 当前项目默认不依赖 Redis；如后续启用缓存/队列，可在这里扩展配置。
REDIS = False

# ************************ MCP配置 ************************ #
# MCP 有 Host/Origin 安全校验。dev 默认只允许本机访问。
# 如果本地通过局域网 IP 调试，例如 http://192.168.1.10:8000，需要把 192.168.1.10:8000 加到 HOSTS，
# 并把 http://192.168.1.10:8000 加到 ORIGINS。
MCP_ALLOWED_HOSTS = ['127.0.0.1:*', 'localhost:*', '[::1]:*']
MCP_ALLOWED_ORIGINS = ['http://127.0.0.1:*', 'http://localhost:*', 'http://[::1]:*']

# ************************ 文件存储配置 ************************ #
# FILE_STORAGE_BACKEND 支持：
#   local：本地文件，保存到 MangoServer/runtime/media，适合开发环境。
#   minio：S3/MinIO 兼容对象存储，适合开源 docker-compose demo。
#   tos：火山 TOS，适合自定义 S3 兼容部署。
FILE_STORAGE_BACKEND = 'local'

# ************************ 本地私有覆盖 ************************ #
# 可选：创建 src/settings/database.json 覆盖数据库配置，避免把个人数据库信息提交到代码仓库。
# 示例：
# {
#   "mysql_port": 3306,
#   "mysql_db_name": "mango_server",
#   "mysql_user": "root",
#   "mysql_password": "password",
#   "mysql_ip": "127.0.0.1"
# }
IS_TRUE = True
file_name = 'src/settings/database.json'
if os.path.exists(file_name) and IS_TRUE:
    # 读取数据
    with open(file_name, 'r') as file:
        data = json.load(file)

    MYSQL_PORT = data.get('mysql_port', MYSQL_PORT)
    MYSQL_DB_NAME = data.get('mysql_db_name', MYSQL_DB_NAME)
    MYSQL_USER = data.get('mysql_user', MYSQL_USER)
    MYSQL_PASSWORD = data.get('mysql_password', MYSQL_PASSWORD)
    MYSQL_IP = data.get('mysql_ip', MYSQL_IP)
