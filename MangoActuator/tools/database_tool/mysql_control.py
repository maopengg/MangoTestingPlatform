# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
import pymysql
from pymysql.err import InternalError, OperationalError, ProgrammingError

from exceptions.tools_exception import MysqlQueryError, MysqlConnectionError
from models.tools_model import MysqlConingModel
from tools.message.error_msg import ERROR_MSG_0001, ERROR_MSG_0033, ERROR_MSG_0035, ERROR_MSG_0034


class MysqlConnect:

    def __init__(self, mysql_config: MysqlConingModel, is_c: bool = True, is_rud: bool = True):
        self.is_c = is_c
        self.is_rud = is_rud
        try:
            self.connection = pymysql.connect(
                host=mysql_config.host,
                port=mysql_config.port,
                user=mysql_config.user,
                password=mysql_config.password,
                database=mysql_config.db,
                autocommit=True
            )
        except OperationalError:
            raise MysqlConnectionError(*ERROR_MSG_0001)
        except InternalError:
            raise MysqlConnectionError(*ERROR_MSG_0033, value=(mysql_config.db,))

    def __del__(self):
        if self.connection:
            self.close()

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

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
            raise MysqlQueryError(*ERROR_MSG_0034, value=(sql,))
        return result

    def execute(self, sql) -> list[dict] | int | list:
        with self.connection.cursor() as cursor:
            try:
                cursor.execute(sql)
            except ProgrammingError:
                raise MysqlQueryError(*ERROR_MSG_0034, value=(sql,))
            except InternalError:
                raise MysqlQueryError(*ERROR_MSG_0035)
            except OperationalError:
                raise MysqlQueryError(*ERROR_MSG_0034, value=(sql,))
            if sql.strip().upper().startswith('SELECT'):
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
            else:
                result = cursor.rowcount
                self.connection.commit()
                return result


if __name__ == '__main__':
    mysql_connect = MysqlConnect(MysqlConingModel(
        host='61.183.9.60',
        user='root',
        port='23306',
        password='zALL_mysql1',
        db='aigc_AutoUITestPlatform',
    ))
    # 查询是否仍然存在 id 为 6 的记录
    query_result = mysql_connect.execute('SELECT nickname, username FROM user_logs WHERE id = 8;')
    for i in query_result:
        for result1 in i:
            print(i.get(result1))
