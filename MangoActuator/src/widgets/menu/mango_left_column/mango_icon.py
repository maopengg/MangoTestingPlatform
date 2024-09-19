# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-08-16 17:05
# @Author : 毛鹏
from src import *


class MangoIcon(QWidget):
    def __init__(
            self,
            icon_path,
            icon_color
    ):
        super().__init__()

        self._icon_path = icon_path
        self._icon_color = icon_color

        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.icon = QLabel()
        self.icon.setAlignment(Qt.AlignCenter)
        self.set_icon(self._icon_path, self._icon_color)
        self.layout.addWidget(self.icon)

    def set_icon(self, icon_path, icon_color=None):
        color = ""
        if icon_color != None:
            color = icon_color
        else:
            color = self._icon_color

        # 画家/位图
        icon = QPixmap(icon_path)
        painter = QPainter(icon)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(icon.rect(), color)
        painter.end()

        # 设置位图
        self.icon.setPixmap(icon)
