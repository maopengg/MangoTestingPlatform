# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-01-10 16:58
# @Author : 毛鹏
from tools.database.sqlite_connect import SQLiteConnect

sql_statement_1 = 'SELECT * FROM user_info;'
sql_statement_2 = f'INSERT INTO "user_info" ("username", "password", "ip", "port") VALUES (?, ?, ?, ?);'
sql_statement_3 = f'DELETE FROM user_info;'
sql_statement_4 = f'INSERT INTO "test_data" ("key", "value", "type") VALUES (?, ?, ?);'
sql_statement_5 = f'SELECT * FROM test_data WHERE `key` = ?'
sql_statement_6 = f'DELETE FROM test_data WHERE `key` = ?'

if __name__ == '__main__':
    db_handler = SQLiteConnect()
    print(db_handler.execute_sql(sql_statement_1))
