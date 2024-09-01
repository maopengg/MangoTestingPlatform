# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2024-09-01 下午10:01
# @Author : 毛鹏
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


def show_message(self):
    message = MangoMessage(self, "这是一个全局消息提示！")
    # 显示在主窗口顶部中央
    parent_pos = self.mapToGlobal(QPoint(self.width() // 2 - message.width() // 2, 0))
    message.move(parent_pos)
    message.show()


class MangoMessage(QWidget):
    def __init__(self, parent, message):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setFixedHeight(30)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(message)
        layout.addWidget(self.label)

        self.setLayout(layout)
        # 设置背景颜色和边框
        self.setStyleSheet("background-color: rgba(255, 255, 224, 100); border: 1px solid lightgray;")

        # 根据文字长度调整宽度
        font_metrics = QFontMetrics(self.label.font())
        text_width = font_metrics.boundingRect(message).width() + 10
        self.setFixedWidth(text_width)

        # 设置渐隐效果
        self.opacity = 1.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fade_out)
        self.timer.start(50)

    def fade_out(self):
        self.opacity -= 0.05
        self.setWindowOpacity(self.opacity)
        if self.opacity <= 0:
            self.close()
