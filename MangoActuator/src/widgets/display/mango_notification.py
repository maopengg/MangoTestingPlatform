# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午9:53
# @Author : 毛鹏
from src import *


class MangoNotification(QWidget):
    def __init__(self, parent, message, style):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setFixedSize(210, 70)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(message)
        layout.addWidget(self.label)

        self.setLayout(layout)

        # 设置微红色背景色
        self.setStyleSheet(f"background-color: {style}; opacity: 0.39;")

        # 设置渐隐效果
        self.opacity = 1.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fade_out)
        self.timer.start(80)

    def fade_out(self):
        self.opacity -= 0.05
        self.setWindowOpacity(self.opacity)
        if self.opacity <= 0:
            self.close()
