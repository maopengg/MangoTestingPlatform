# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2024-08-24 16:48
# @Author : 毛鹏
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QListWidget, \
    QListWidgetItem, QLabel
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

class Page1(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("这是页面 1 的内容。")
        layout.addWidget(label)
        self.setLayout(layout)

class Page2(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("这是页面 2 的内容。")
        layout.addWidget(label)
        self.setLayout(layout)

# 定义菜单选项和对应的页面类
menu_options = [
    ('页面 1', Page1),
    ('页面 2', Page2),
]

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("带有左侧菜单的应用")

        # 整体布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 左侧菜单
        self.menu_list = QListWidget()
        self.menu_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: none;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px;
                border: none;
                color: #333;
            }
            QListWidget::item:selected {
                background-color: #0078D4;
                color: white;
            }
        """)
        for option, page_class in menu_options:
            item = QListWidgetItem(option)
            self.menu_list.addItem(item)

        main_layout.addWidget(self.menu_list)

        # 右侧页面切换区域
        self.stacked_widget = QStackedWidget()
        for _, page_class in menu_options:
            page = page_class()
            self.stacked_widget.addWidget(page)

        main_layout.addWidget(self.stacked_widget)

        # 连接菜单点击信号
        self.menu_list.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())