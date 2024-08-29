# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidgetItem, QAbstractItemView, QHeaderView, QHBoxLayout, \
    QPushButton, QSizePolicy
from PySide6.QtCore import Qt

from src.network.http_client import HttpClient
from src.widgets import *


class PagePage(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.table_widget = PyTableWidget()
        self.table_widget.setColumnCount(8)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_widget.setHorizontalHeaderLabels(
            ["ID", "更新时间", "模块名称", "项目产品名称", "创建时间", "页面名称", "URL", '操作'])
        self.layout.addWidget(self.table_widget)
        self.setLayout(self.layout)

    def show_data(self):
        data_list = HttpClient.page_list()
        for row, item in enumerate(data_list):
            self.table_widget.insertRow(row)
            self.table_widget.setItem(row, 0, QTableWidgetItem(str(item["id"])))
            self.table_widget.setItem(row, 1, QTableWidgetItem(item["update_time"]))
            self.table_widget.setItem(row, 2, QTableWidgetItem(item["module"]["name"]))
            self.table_widget.setItem(row, 3, QTableWidgetItem(item["project_product"]["name"]))
            self.table_widget.setItem(row, 4, QTableWidgetItem(item["create_Time"]))
            self.table_widget.setItem(row, 5, QTableWidgetItem(item["name"]))
            self.table_widget.setItem(row, 6, QTableWidgetItem(item["url"]))
            # 创建一个操作栏的小部件，用于放置三个按钮
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_widget.setLayout(action_layout)

            button1 = QPushButton("编辑")
            button2 = QPushButton("添加")
            button3 = QPushButton("···")
            button1.clicked.connect(self.click1)
            button2.clicked.connect(self.click2)
            button3.clicked.connect(self.click3)
            button_style = "QPushButton { background-color: transparent; border: none; padding: 0; color: blue; font-size: 11px; }"

            button1.setStyleSheet(button_style)
            button2.setStyleSheet(button_style)
            button3.setStyleSheet(button_style)
            button1.setCursor(QCursor(Qt.PointingHandCursor))
            button2.setCursor(QCursor(Qt.PointingHandCursor))
            button3.setCursor(QCursor(Qt.PointingHandCursor))
            action_layout.addWidget(button1)
            action_layout.addWidget(button2)
            action_layout.addWidget(button3)

            # 将操作栏小部件添加到表格的“操作”列
            self.table_widget.setCellWidget(row, 7, action_widget)


    def click1(self):
        print('点击了1')
    def click2(self):
        print('点击了2')
    def click3(self):
        print('点击了3')