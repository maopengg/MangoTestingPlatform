# @Project: MangoServer
# @Description:
# @Time   : 2022-11-17 20:27
# @Author : 毛鹏
import logging

import pymysql
from pymysql.err import InternalError, OperationalError, ProgrammingError

from PyAutoTest.exceptions.tools_exception import MySQLConnectionFailureError, MysqlConnectionError, \
    MysqlQueryError
from PyAutoTest.models.tools_model import MysqlConingModel
from PyAutoTest.tools.view.error_msg import ERROR_MSG_0023, ERROR_MSG_0024, ERROR_MSG_0025, ERROR_MSG_0009

log = logging.getLogger('system')


class MysqlConnect:
    """mysql封装"""

    def __init__(self, mysql_config: MysqlConingModel, is_c: bool = True, is_rud: bool = True):
        self.is_c = is_c
        self.is_rud = is_rud
        try:
            self.connection = pymysql.connect(
                host=mysql_config.host,
                port=mysql_config.port,
                user=mysql_config.user,
                password=mysql_config.password,
                database=mysql_config.database,
                autocommit=True
            )
        except OperationalError:
            raise MySQLConnectionFailureError(*ERROR_MSG_0023)
        except InternalError:
            raise MysqlConnectionError(*ERROR_MSG_0009, value=(mysql_config.db,))

    def __del__(self):
        self.close()

    def close(self):
        if hasattr(self, 'connection') and self.connection:
            self.connection.close()

    def condition_execute(self, sql: str) -> list[dict] | list | int | None:
        sql = sql.strip().upper()
        result = None
        if sql.startswith('SELECT'):
            if self.is_c:
                result = self.execute(sql)
        elif sql.startswith('INSERT') or sql.startswith('UPDATE') or sql.startswith('DELETE'):
            if self.is_rud:
                result = self.execute(sql)
        else:
            raise MysqlQueryError(*ERROR_MSG_0025, value=(sql,))
        return result

    def execute(self, sql: str) -> list[dict] | int:
        """
         执行 SQL 查询或更新、删除、新增操作
         :param sql: SQL 语句
         :return: 查询返回 list[dict]，更新、删除、新增返回行数
         """
        with self.connection.cursor() as cursor:
            try:
                cursor.execute(sql)
            except ProgrammingError:
                raise MysqlQueryError(*ERROR_MSG_0025, value=(sql,))
            except InternalError:
                raise MysqlQueryError(*ERROR_MSG_0024)
            except OperationalError:
                raise MysqlQueryError(*ERROR_MSG_0025, value=(sql,))
            if sql.strip().upper().startswith('SELECT'):
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
            else:
                result = cursor.rowcount
                self.connection.commit()
                return result
