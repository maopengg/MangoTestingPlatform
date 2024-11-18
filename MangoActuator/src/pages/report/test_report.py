# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-24 17:10
# @Author : 毛鹏
from mango_ui import *

from src.network import HTTP
from .test_report_dict import *
from ..parent.table import TableParent


class TestReportPage(TableParent):
    def __init__(self, parent):
        super().__init__(parent, search_data=search_data)
        self.subpage_value = 'test_report_detailed'
        self.get = HTTP.get_test_suite_report
        self.post = HTTP.post_test_suite_report
        self.put = HTTP.put_test_suite_report
        self._delete = HTTP.delete_test_suite_report
        self.layout_v = MangoVBoxLayout()
        self.layout.addLayout(self.layout_v)
        self.layout_h = MangoHBoxLayout()
        self.layout_v.addLayout(self.layout_h, 3)
        self.layout_v_1 = MangoVBoxLayout()
        self.layout_h.addLayout(self.layout_v_1, 2)
        self.pie_plot_1 = MangoPiePlot()
        self.layout_v_1.addWidget(self.pie_plot_1)
        self.layout_v_2 = MangoVBoxLayout()
        self.layout_h.addLayout(self.layout_v_2, 8)
        self.line_plot_1 = MangoLinePlot('', '数量', '周')
        self.layout_v_2.addWidget(self.line_plot_1)
        self.table_column = [TableColumnModel(**i) for i in table_column]
        self.table_menu = [TableMenuItemModel(**i) for i in table_menu]
        self.table_widget = TableList(self.table_column, self.table_menu, )
        self.table_widget.pagination.click.connect(self.pagination_clicked)
        self.table_widget.clicked.connect(self.callback)
        self.layout_v.addWidget(self.table_widget, 7)

    def show_data(self, is_refresh=False):
        response_model = HTTP.result_week()
        self.line_plot_1.draw([
            {'name': '成功', 'value': response_model.data.get('success')},
            {'name': '失败', 'value': response_model.data.get('fail')}
        ])
        self.pie_plot_1.draw([
            {'name': '失败数', 'value': response_model.data.get('failSun')},
            {'name': '成功数', 'value': response_model.data.get('successSun')}
        ])
        super().show_data(is_refresh)
