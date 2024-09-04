# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2024-09-01 下午10:01
# @Author : 毛鹏
from src import *


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
