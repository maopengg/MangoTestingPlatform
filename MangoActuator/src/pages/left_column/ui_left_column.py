from PySide6.QtCore import *
from PySide6.QtWidgets import *


class LeftColumn:
    def setup_ui(self, left_column):
        left_column.resize(240, 600)
        self.main_pages_layout = QVBoxLayout(left_column)
        self.main_pages_layout.setSpacing(0)
        self.main_pages_layout.setContentsMargins(5, 5, 5, 5)
        self.menus = QStackedWidget(left_column)
        self.main_pages_layout.addWidget(self.menus)
        self.menus.setCurrentIndex(0)
        QMetaObject.connectSlotsByName(left_column)
