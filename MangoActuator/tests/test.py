# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-01-06 18:32
# @Author : 毛鹏
import re

from mangokit import MysqlConingModel, MysqlConnect

mysql_config = MysqlConingModel(
    host='172.22.68.122',
    port=3306,
    user='root',
    password='mP123456&',
    database='mango_server'
)
mysql_conn = MysqlConnect(mysql_config)

dict_data = mysql_conn.execute("SELECT * FROM `ui_case_steps_detailed`;")
for i in dict_data:
    case_data = re.sub(r'\$\{(.*?)\}', r'${{\1}}', i.get('case_data'))
    case_cache_data = re.sub(r'\$\{(.*?)\}', r'${{\1}}', i.get('case_cache_data'))
    case_cache_ass = re.sub(r'\$\{(.*?)\}', r'${{\1}}', i.get('case_cache_ass'))
    update_query = f"UPDATE `ui_case_steps_detailed` SET `case_data` = '{case_data}', `case_cache_data` ='{case_cache_data}', `case_cache_ass` ='{case_cache_ass}' WHERE `id` = {i.get('id')};"
    print(update_query)
    mysql_conn.execute(update_query)

# 关闭数据库连接（假设 MysqlConnect 有 close 方法）
mysql_conn.close()