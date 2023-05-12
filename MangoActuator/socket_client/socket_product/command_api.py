# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:25
# @Author : 毛鹏

from utils.ope_win.cmd import cmd


class ExternalAPI:

    @staticmethod
    def cmd(cmd_data):
        return cmd(cmd_data)
