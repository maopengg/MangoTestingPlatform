# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2024-09-01 下午9:53
# @Author : 毛鹏

from PySide6.QtCore import *
from PySide6.QtWidgets import *


def show_notification(self):
    notification = MangoNotification(self, "这是一个通知消息！")
    # 获取主窗口右上角位置
    parent_pos = self.mapToGlobal(QPoint(self.width() - notification.width() - 10, 20))
    notification.move(parent_pos)
    notification.show()


class MangoNotification(QWidget):
    def __init__(self, parent, message):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setFixedSize(210, 70)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(message)
        layout.addWidget(self.label)

        self.setLayout(layout)

        # 设置微红色背景色
        self.setStyleSheet("background-color: rgba(255, 192, 203, 100);")

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
