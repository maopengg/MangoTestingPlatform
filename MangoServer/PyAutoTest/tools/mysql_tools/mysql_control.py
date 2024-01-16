# @Project: MangoServer
# @Description:
# @Time   : 2022-11-17 20:27
# @Author : 毛鹏
import logging

import pymysql
from pymysql.err import ProgrammingError, OperationalError

from PyAutoTest.exceptions.tools_exception import MySQLConnectionFailureError, SQLGrammarError
from PyAutoTest.models.tools_model import MysqlConingModel

logger = logging.getLogger('system')


class MysqlClient:
    """mysql封装"""

    def __init__(self, database: MysqlConingModel):
        self.conn = None
        self.cur = None
        try:
            self.conn = pymysql.connect(
                host=database.host,
                port=database.port,
                user=database.user,
                password=database.password,
                database=database.db
            )

        # 使用 cursor 方法获取操作游标，得到一个可以执行sql语句，并且操作结果为字典返回的游标
            self.cur = self.conn.cursor(cursor=pymysql.cursors.DictCursor)
        except OperationalError:
            raise MySQLConnectionFailureError('请检查mysql配置或确保该地址在服务器中可以被连接')

    def __del__(self):
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()

    def execute(self, sql: str) -> list[dict] | int:
        """
         执行 SQL 查询或更新、删除、新增操作
         :param sql: SQL 语句
         :return: 查询返回 list[dict]，更新、删除、新增返回行数
         """
        try:
            if sql.strip().lower().startswith('select'):
                # 查询操作
                self.cur.execute(sql)
                result = [dict(row) for row in self.cur.fetchall()]
                return result
            else:
                # 更新、删除、新增操作
                rows_affected = self.cur.execute(sql)
                self.conn.commit()
                return rows_affected
        except ProgrammingError:
            raise SQLGrammarError('sql语法错误，请检查sql')
