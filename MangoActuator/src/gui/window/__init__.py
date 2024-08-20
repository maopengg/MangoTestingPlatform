# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-09-28 16:03
# @Author : 毛鹏
import sys
from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QPushButton, \
    QHBoxLayout, QMenu, QToolButton


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("带无边框按钮的表格示例")
        self.setGeometry(100, 100, 400, 300)

        layout = QVBoxLayout(self)
        self.table = QTableWidget(10, 2)  # 10行2列

        for row in range(10):
            # 在第一列添加文本
            self.table.setItem(row, 0, QTableWidgetItem(f"Item {row}"))

            # 创建一个水平布局来放置三个按钮
            button_layout = QHBoxLayout()

            # 添加“编辑”按钮
            edit_button = QPushButton("编辑")
            edit_button.setStyleSheet("border: none;")
            edit_button.clicked.connect(lambda _, r=row: self.on_button_click(r, "编辑"))
            button_layout.addWidget(edit_button)

            # 添加“详情”按钮
            detail_button = QPushButton("详情")
            detail_button.setStyleSheet("border: none;")
            detail_button.clicked.connect(lambda _, r=row: self.on_button_click(r, "详情"))
            button_layout.addWidget(detail_button)

            # 添加“更多”按钮
            more_button = QToolButton()
            more_button.setText("更多")
            more_button.setStyleSheet("border: none;")
            more_button.setPopupMode(QToolButton.InstantPopup)  # 设置为即时弹出模式
            more_button.setMenu(self.create_more_menu(row))  # 设置悬浮菜单
            button_layout.addWidget(more_button)

            # 将布局设置为单元格的小部件
            button_widget = QWidget()
            button_widget.setLayout(button_layout)
            self.table.setCellWidget(row, 1, button_widget)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def create_more_menu(self, row):
        menu = QMenu()
        # 添加子菜单项
        debug_action = menu.addAction("调试")
        delete_action = menu.addAction("删除")
        result_action = menu.addAction("结果")

        # 连接菜单项的点击事件
        debug_action.triggered.connect(lambda: self.on_more_action(row, "调试"))
        delete_action.triggered.connect(lambda: self.on_more_action(row, "删除"))
        result_action.triggered.connect(lambda: self.on_more_action(row, "结果"))

        return menu

    def on_button_click(self, row, action):
        print(f"{action} 按钮在第 {row} 行被点击")

    def on_more_action(self, row, action):
        print(f"{action} 菜单项在第 {row} 行被点击")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
