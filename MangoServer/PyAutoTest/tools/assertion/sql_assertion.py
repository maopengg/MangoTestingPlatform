# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-11-20 9:47
# @Author : 毛鹏
import asyncio

from tools.database.mysql_control import MysqlConnect


class SqlAssertion:
    """sql断言"""
    mysql_connect: MysqlConnect = None

    @staticmethod
    async def sql_is_equal(sql: str, expect: list[dict]):
        """值相等"""
        result = await SqlAssertion.mysql_connect.select(sql)
        assert all(dict2 in result for dict2 in expect), "列表不相等"
        # result = await SqlAssertion.mysql_obj.select(sql)
        # 检查list1中的每个字典是否存在于list2中
        # assert all(dict1 in expect for dict1 in result), "列表不相等"
        # 检查list2中的每个字典是否存在于list1中


if __name__ == '__main__':
    _sql = "SELECT id,`name`,`status` FROM `project`;"
    _expect = [{'id': 2, 'name': '1CDXP', 'status': 1}, {'id': 5, 'name': 'AIGC', 'status': 1},
               {'id': 10, 'name': 'DESK', 'status': 1}, {'id': 11, 'name': 'AIGC-SaaS', 'status': 1}]

    # mysql_model = MysqlDBModel(host='61.183.9.60',
    #                            port=23306,
    #                            user='root',
    #                            password='zALL_mysql1',
    #                            db='aigc_AutoUITestPlatform')
    # mysql = MysqlDB()
    # await mysql.connect(mysql_model)
    # SqlAssertion.mysql_obj = mysql

    # 创建新的事件循环对象
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    asyncio.run(SqlAssertion.sql_is_equal(sql=_sql, expect=_expect))
    # loop.close()
