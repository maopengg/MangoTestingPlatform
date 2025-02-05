# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-01-24 11:36
# @Author : 毛鹏

from mangokit import MysqlConingModel, MysqlConnect

mysql_config = MysqlConingModel(
    host='172.22.68.122',
    port=3306,
    user='root',
    password='mP123456&',
    database='mango_server'
)
mysql_conn = MysqlConnect(mysql_config)
