# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-07-12 14:13
# @Author : 毛鹏
import json
import os

# ************************ 数据源类型 ************************ #

IS_SQLITE = False  # 是否选用mysql作为数据源

# ************************ Mysql配置 ************************ #
mysql_port = 3306
mysql_db_name = 'mango_server'
mysql_user = 'root'
mysql_password = 'mP123456&'
mysql_ip = '127.0.0.1'

# 个人配置，开源用户忽略这部分代码
file_name = 'PyAutoTest/settings/database.json'
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

# ************************ DEBUG配置 ************************ #
DEBUG = True

# ************************ REDIS配置 ************************ #

REDIS = False

# ************************ 是否允许删除 ************************ #
IS_DELETE = True
