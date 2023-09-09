# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-04-29 11:20
# @Author : 毛鹏
from PyAutoTest.models.ui_data_model import CaseResult


class UIConsumer:

    def ui_debug_case_result(self, data: dict):
        data = CaseResult(**data)
