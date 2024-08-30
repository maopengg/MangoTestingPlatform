# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-29 15:32
# @Author : 毛鹏
from PySide6.QtWidgets import QVBoxLayout, QHeaderView, QAbstractItemView, QWidget

from src.widgets import PyTableWidget


class TableList(QWidget):
    def __init__(self, column_count: int, row_column: list[str]):
        super().__init__()
        self.layout = QVBoxLayout()
        self.table_widget = PyTableWidget()
        self.table_widget.setColumnCount(column_count)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_widget.setHorizontalHeaderLabels(row_column)
        self.layout.addWidget(self.table_widget)
        self.setLayout(self.layout)
