# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-24 17:10
# @Author : 毛鹏
from src.network import Http
from .test_report_dict import *
from ..parent.table import TableParent


class TestReportPage(TableParent):
    def __init__(self, parent):
        super().__init__(parent,
                         search_data=search_data,
                         table_column=table_column,
                         table_menu=table_menu)
        self.get = Http.get_test_suite_report
        self.post = Http.post_test_suite_report
        self.put = Http.put_test_suite_report
        self._delete = Http.delete_test_suite_report
