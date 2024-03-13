import os
import sqlite3
from typing import Union

from tools import Initialization


class SQLiteHandler:

    def __init__(self):
        self.db_name = os.path.join(Initialization.cache, 'cache.db')
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()

    def execute_sql(self, sql_query: str, data: tuple = None) -> Union[list[dict], int]:
        if data:
            self.cursor.execute(sql_query, data)
        else:
            self.cursor.execute(sql_query)
        if sql_query.strip().split()[0].upper() == 'SELECT':
            rows = self.cursor.fetchall()
            column_names = [description[0] for description in self.cursor.description]
            result_list = [dict(zip(column_names, row)) for row in rows]
            return result_list
        elif sql_query.strip().split()[0].upper() in ['INSERT', 'UPDATE']:
            self.conn.commit()
            return self.cursor.rowcount
        elif sql_query.strip().split()[0].upper() == 'DELETE':
            self.conn.commit()
            return self.cursor.rowcount
        elif sql_query.strip().split()[0].upper() == 'CREATE':
            self.conn.commit()
            return self.cursor.rowcount
        else:
            raise Exception('sql语句错误')

    def close_connection(self) -> None:
        self.conn.close()

    def __del__(self):
        self.conn.close()


create_table_query1 = '''
CREATE TABLE "test_data" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "key" TEXT NOT NULL,
  "value" TEXT,
  "case_id" TEXT,
  "type" INTEGER,
  "internal" INTEGER
);
'''
create_table_query2 = '''
CREATE TABLE "user_info" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "username" TEXT NOT NULL,
  "password" TEXT,
  "ip" TEXT,
  "port" TEXT
);
'''
# 使用示例
db_handler = SQLiteHandler()
for i in [create_table_query1, create_table_query2]:
    try:
        db_handler.execute_sql(i)
    except sqlite3.OperationalError:
        pass
