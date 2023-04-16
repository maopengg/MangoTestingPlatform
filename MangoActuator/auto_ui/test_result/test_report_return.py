# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-15 23:06
# @Author : 毛鹏
from utlis.mysql.mysql_control import MysqlDB


class TestReportReturn:
    my = MysqlDB()

    @classmethod
    def ele_res_insert(cls, ele_name: str or None = None,
                       existence: int or None = None,
                       state: int or None = None,
                       case_id: str or None = None,
                       case_group_id: str or None = None,
                       team_id: str or None = None,
                       test_obj_id: int or None = None,
                       msg: str or None = None,
                       picture: str or None = None):
        sql = f"""
        INSERT INTO
        ui_result (ele_name, existence, state, case_id, case_group_id, team_id, test_obj_id, msg, picture)
        VALUES 
        ({ele_name}, {existence}, {state}, {case_id},{case_group_id},{team_id}, {test_obj_id}, {msg}, {picture});
          """
        print(sql)
        res = cls.my.execute(sql)
        return True if res == 1 else False
