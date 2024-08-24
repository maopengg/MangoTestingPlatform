# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-21 10:28
# @Author : 毛鹏
import sys
from PySide6.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout
from PySide6.QtCore import Qt
import sys
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtGui import QColor, QPainter, QPen, QBrush
from PySide6.QtCore import Qt

class FluentButton(QPushButton):
    def __init__(self, text=None, parent=None):
        super().__init__( text=text,parent=parent,)
        self.setFixedSize(150, 40)
        self.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #000000;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #E6E6E6;
            }
            QPushButton:pressed {
                background-color: #D9D9D9;
            }
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.isDown():
            painter.setBrush(QBrush(QColor("#D9D9D9")))
        elif self.underMouse():
            painter.setBrush(QBrush(QColor("#E6E6E6")))
        else:
            painter.setBrush(QBrush(QColor("white")))
        painter.setPen(QPen(Qt.NoPen))
        painter.drawRoundedRect(self.rect(), 5, 5)
        super().paintEvent(event)

    def mousePressEvent(self, event):
        """
        重写 mousePressEvent 方法以处理鼠标按下事件。

        参数：
        - event：鼠标按下事件。
        """
        print('点击了')
        super().mousePressEvent(event)
        # 可以在这里添加按钮按下时的特定逻辑

    def mouseReleaseEvent(self, event):
        """
        重写 mouseReleaseEvent 方法以处理鼠标释放事件。

        参数：
        - event：鼠标释放事件。
        """
        super().mouseReleaseEvent(event)
        # 可以在这里添加按钮释放时的特定逻辑

    def enterEvent(self, event):
        """
        重写 enterEvent 方法以处理鼠标进入按钮区域事件。

        参数：
        - event：鼠标进入事件。
        """
        super().enterEvent(event)
        # 可以在这里添加鼠标进入按钮区域时的特定逻辑

    def leaveEvent(self, event):
        """
        重写 leaveEvent 方法以处理鼠标离开按钮区域事件。

        参数：
        - event：鼠标离开事件。
        """
        super().leaveEvent(event)
        # 可以在这里添加鼠标离开按钮区域时的特定逻辑