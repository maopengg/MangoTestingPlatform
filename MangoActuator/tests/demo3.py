# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-04 14:11
# @Author : 毛鹏
# coding:utf-8
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QComboBox


class Demo(QWidget):

    def __init__(self):
        super().__init__()
        self.comboBox = QComboBox(self)
        self.hBoxLayout = QHBoxLayout(self)

        self.comboBox.setPlaceholderText("选择一个脑婆")

        items = ['shoko 🥰', '西宫硝子', '宝多六花', '小鸟游六花']
        self.comboBox.addItems(items)
        self.comboBox.setCurrentIndex(-1)

        self.comboBox.currentTextChanged.connect(print)

        self.resize(500, 500)
        self.hBoxLayout.addWidget(self.comboBox, 0, Qt.AlignCenter)
        self.setStyleSheet('Demo{background:white}')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Demo()
    w.show()
    app.exec()
