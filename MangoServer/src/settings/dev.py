# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-07-12 14:13
# @Author : 毛鹏

# ************************ 数据源类型 ************************ #

IS_SQLITE = False  # 是否选用sqlite作为数据源，默认使用mysql

# ************************ Mysql配置 ************************ #
MYSQL_PORT = 3306
MYSQL_DB_NAME = 'dev_mango_server'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'mP123456&'
MYSQL_IP = '192.168.75.157'

# ************************ DEBUG配置 ************************ #
# 这里也控制了是否使用minio
# True开启debug就不会使用minio
# 生产环境=True，生产环境=False，使用minio
DEBUG = True
IS_DEBUG_LOG = True
# ************************ REDIS配置 ************************ #

REDIS = False
# ************************ Minio配置 ************************ #
MINIO_STORAGE_ENDPOINT = '192.168.1.100:9000'
MINIO_STORAGE_ACCESS_KEY = 'R3SrN5q9XGWj1n28wpG9'  # ACCESS_KEY
MINIO_STORAGE_SECRET_KEY = 'LliOFBMjp19jFTUw3byUGxgaj6GnmUdsEpRyFjw4'  # SECRET_KEY
MINIO_STORAGE_USE_HTTPS = False  # 如果使用 HTTPS，设置为 True
MINIO_STORAGE_MEDIA_BUCKET_NAME = 'mango-file'  # 桶名称
MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = True  # 桶不存在时自动创建

# ************************ 是否允许删除 ************************ #
IS_DELETE = True
# *************** 是否发送error日志协助芒果修复问题 *************** #
IS_SEND_MAIL = False

# **************** 个人配置，开源用户忽略这部分代码 **************** #
# file_name = 'src/settings/database.json'
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
