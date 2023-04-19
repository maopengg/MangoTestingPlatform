# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-15 23:07
# @Author : 毛鹏
import asyncio

from utlis.client import client_socket
from utlis.client.server_enum_api import ServerEnumAPI
from utlis.mysql.mysql_control import MysqlDB


class ResultMain:
    my = MysqlDB()

    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg

    def res_collect(self):
        # self.res_data.append()
        pass

    async def res_dispatch(self):
        await asyncio.gather(self.notification_send(),
                             self.test_res_analysis()
                             )

    async def notification_send(self):
        await client_socket.ClientWebSocket.active_send(
            code=code,
            func=ServerEnumAPI.NOTICE_MAIN.value,
            msg=msg,
            end=True,
            data='')

    @classmethod
    async def test_res_analysis(cls):
        return await cls.ele_res_insert(
            ele_name='新增商品按钮',
            existence=1,
            state=0,
            case_id='新建普通商品',
            case_group_id='null',
            team_id='应用组',
            test_obj_id='zshop预发环境',
            msg='元素不存在',
            picture='www.baidu.com'
        )

    @classmethod
    async def ele_res_insert(cls, ele_name: str or None = None,
                             existence: int or None = None,
                             state: int or None = None,
                             case_id: str or None = None,
                             case_group_id: str = None,
                             team_id: str or None = None,
                             test_obj_id: int or None = None,
                             msg: str or None = None,
                             picture: str or None = None):
        sql = f"""
        INSERT INTO
        ui_result (ele_name, existence, state, case_id, case_group_id, team_id, test_obj_id, msg, picture)
        VALUES
        ('{ele_name}', {existence}, {state}, '{case_id}',{case_group_id},'{team_id}', '{test_obj_id}', '{msg}', '{picture}');
          """
        res = cls.my.execute(sql)
        return True if res == 1 else False


if __name__ == '__main__':
    code = 200
    msg = 'haah'
    r = ResultMain(code, msg)
    asyncio.run(r.res_dispatch())
