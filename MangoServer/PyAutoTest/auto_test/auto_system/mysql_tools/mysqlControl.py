# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description:
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏

import pymysql


class Mysql:
    """封装数据库的连接信息"""

    def __init__(self):
        self.conn = pymysql.connect(
            host="114.116.40.29",
            port=3306,
            user='root',
            password='m729164035.',
            database='api_auto'
        )

    def sql_select(self, case_name):
        cursor = self.conn.cursor()
        # 定义将要执行的sql语句
        # 拼接sql
        case_name = "'" + case_name + "'"
        # sql = "SELECT * FROM case_run WHERE" + f" case_name = {case_name}"
        # 返回字典数据类型
        cursor.execute(sql)
        # 取出结果并返回全部
        # ret = cursor.fetchall()
        # 取出结果并返回一条
        ret = cursor.fetchone()
        # 取出结果并返回 条数
        # ret = cursor.fetchmany(1)
        return ret
        # ret3 = cursor.fetchone()  # 取一条

    def __del__(self):
        self.conn.close()


if __name__ == '__main__':
    sql = Mysql()
    sql.sql_select("首页banner")
