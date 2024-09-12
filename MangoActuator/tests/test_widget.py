# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-04 17:43
# @Author : 毛鹏
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication

from src.models.gui_model import TableMenuItemModel, TableColumnModel
from src.widgets import *

table_column = [
    {'key': 'name', 'name': '元素名称', 'item': '', 'width': 10},
    {'key': 'exp', 'name': '表达式类型', 'item': '', 'width': 10},
    {'key': 'loc', 'name': '定位表达式', 'item': '', 'width': 50},
    {'key': 'is_iframe', 'name': '是否在iframe中', 'item': '', 'width': 5},
    {'key': 'sleep', 'name': '等待时间（秒）', 'item': '', 'width': 5},
    {'key': 'sub', 'name': '元素下标（1开始）', 'item': '', 'width': 5},
    {'key': 'ope', 'name': '操作', 'item': '', 'width': 15},
]
table_menu = [
    {'name': '调试', 'action': 'debug'},
    {'name': '编辑', 'action': 'edit'},
    {'name': '删除', 'action': 'delete'}
]


class MyQWidget(QWidget):
    data = [{'id': 39,
             'page': {'id': 20, 'update_time': '2024-08-08 17:42:35', 'create_Time': '2024-08-07T23:37:22.516852',
                      'name': '百度查询页', 'url': '/', 'project_product': 11, 'module': 28},
             'create_time': '2024-08-07 23:38:58', 'update_time': '2024-08-08 14:23:12', 'name': '输入框', 'exp': 3,
             'loc': 'class="bg s_ipt_wr new-pmd quickdelete-wrap"', 'sleep': 1, 'sub': None, 'is_iframe': 0}]

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)  # 设置间距为0
        self.resize(800, 400)
        self.table_column = [TableColumnModel(**i) for i in table_column]
        self.table_menu = [TableMenuItemModel(**i) for i in table_menu]
        self.table_widget = MangoTableWidget(self.table_column, self.table_menu)
        self.table_widget.set_value(self.data)
        self.layout.addWidget(self.table_widget)
        self.setLayout(self.layout)


if __name__ == '__main__':
    app = QApplication([])
    window = MyQWidget()
    window.show()
    app.exec()
