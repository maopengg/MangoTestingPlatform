# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-07-12 14:13
# @Author : 毛鹏
# *********************** 是否初始化项目 *********************** #

INIT_MANGO_TESTING_PLATFORM = True  # 可以初始化部分原始数据，快速开展简单的自动化任务

# ************************ 数据源类型 ************************ #

IS_SQLITE = False  # 是否选用mysql作为数据源

# ************************ Mysql配置 ************************ #

mysql_db_name = 'mango_server'
mysql_user = 'root'
mysql_password = '123456'
mysql_ip = 'IP'
mysql_port = 3306

# ************************ DEBUG配置 ************************ #
DEBUG = False

# ************************ REDIS配置 ************************ #

REDIS = False

# ************************ 是否允许删除 ************************ #
IS_DELETE = True
