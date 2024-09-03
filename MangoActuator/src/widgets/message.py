# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2024-09-01 下午10:01
# @Author : 毛鹏
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from src.models.service_http_model import ResponseModel
from src.settings.settings import THEME




def info_message(parent, text):
    message = MangoMessage(parent, text, THEME.pink)
    parent_pos = parent.mapToGlobal(QPoint(parent.width() // 2 - message.width() // 2, 0))
    message.move(parent_pos)
    message.show()


def success_message(parent, text):
    message = MangoMessage(parent, text, THEME.green)
    parent_pos = parent.mapToGlobal(QPoint(parent.width() // 2 - message.width() // 2, 0))
    message.move(parent_pos)
    message.show()


def warning_message(parent, text):
    message = MangoMessage(parent, text, THEME.yellow)
    parent_pos = parent.mapToGlobal(QPoint(parent.width() // 2 - message.width() // 2, 0))
    message.move(parent_pos)
    message.show()


def error_message(parent, text):
    message = MangoMessage(parent, text, THEME.red)
    parent_pos = parent.mapToGlobal(QPoint(parent.width() // 2 - message.width() // 2, 0))
    message.move(parent_pos)
    message.show()


def response_message(parent, response: ResponseModel):
    if response.code == 200:
        success_message(parent, response.msg)
    else:
        error_message(parent, response.msg)

class MangoMessage(QWidget):
    def __init__(self, parent, message, style):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setFixedHeight(30)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 0, 0, 0)
        self.label = QLabel(message)
        layout.addWidget(self.label)

        self.setLayout(layout)
        # 设置背景颜色和边框
        self.setStyleSheet(f"background-color: {style}; border: 1px solid lightgray; opacity: 0.39;")

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
