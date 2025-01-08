# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-01-10 16:58
# @Author : 毛鹏
import sqlite3

from mangokit import SQLiteConnect

from src.tools import project_dir

sql_statement_1 = 'SELECT * FROM user_info;'
sql_statement_2 = f'INSERT INTO "user_info" ("username", "password", "ip", "port") VALUES (?, ?, ?, ?);'
sql_statement_3 = f'DELETE FROM user_info;'

create_table_query2 = '''
CREATE TABLE "user_info" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "username" TEXT NOT NULL,
  "password" TEXT,
  "ip" TEXT,
  "port" TEXT
);
'''

db_handler = SQLiteConnect(project_dir.cache_file())
for i in [create_table_query2]:
    try:
        db_handler.execute(i)
    except sqlite3.OperationalError:
        pass

if __name__ == '__main__':
    db_handler = SQLiteConnect(project_dir.cache_file())
    print(db_handler.execute(sql_statement_1))
