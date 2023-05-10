# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-15 23:07
# @Author : 毛鹏
import asyncio

from utils.logs.log_control import ERROR
from utils.mysql.mysql_control import MysqlDB


class ResultMain:
    my = MysqlDB()

    async def res_dispatch(self, code: int, mail_msg: str, ele_name: str,
                           existence: int,
                           state: int,
                           case_id: str,
                           case_group_id: str = None,
                           team_id: str or None = None,
                           test_obj_id: int or None = None,
                           msg: str or None = None,
                           picture_path: str or None = None):
        await asyncio.gather(self.notification_send(code, mail_msg),
                             self.ele_res_insert(ele_name, existence, state, case_id, case_group_id, team_id,
                                                 test_obj_id, msg, picture_path)
                             )

    @classmethod
    async def notification_send(cls, code: int, mail_msg: str):
        from socket_client import client
        from socket_client.queue_ import ServerEnumAPI
        await client.active_send(
            code=code,
            func=ServerEnumAPI.NOTICE_MAIN.value,
            msg=mail_msg,
            end=True,
            data='')

    @classmethod
    async def ele_res_insert(cls, ele_name: str,
                             existence: int,
                             state: int,
                             case_id: str,
                             case_group_id: str = None,
                             team_id: str or None = None,
                             test_obj_id: int or None = None,
                             msg: str or None = None,
                             picture_path: str or None = None):
        sql = f"""
        INSERT INTO
        ui_result (ele_name, existence, state, case_id, case_group_id, team_id, test_obj_id, msg, picture)
        VALUES
        ('{ele_name}', {existence}, {state}, '{case_id}',{case_group_id},'{team_id}', '{test_obj_id}', '{msg}',
         '{picture_path}');
          """
        res = cls.my.execute(sql)
        True if res == 1 else ERROR.logger.error(
            f"""数据写入错误！请联系管理员检查写入数据
            {ele_name, existence, state, case_id, case_group_id, team_id, test_obj_id, msg, picture_path}""")

    @classmethod
    async def web_notice(cls, code: int, web_msg: str):
        from socket_client import client
        await client.active_send(
            code=code,
            func=None,
            msg=web_msg,
            end=True,
            data='')


if __name__ == '__main__':
    # code = 200
    # msg = 'haah'
    # r = ResultMain(code, msg)
    # asyncio.run(r.res_dispatch())
    pass
