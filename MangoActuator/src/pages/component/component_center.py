# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-28 16:33
# @Author : 毛鹏
from PySide6.QtCore import QRect, QSize, QCoreApplication, QMetaObject
from PySide6.QtCore import QTimer
from PySide6.QtGui import Qt, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QHBoxLayout, QLabel, QScrollArea


class ExamplePage(QWidget):
    def __init__(self, text):
        super().__init__()
        self.component_center = QWidget()
        self.page_2_layout = QVBoxLayout(self.component_center)
        self.page_2_layout.setSpacing(5)
        self.page_2_layout.setContentsMargins(5, 5, 5, 5)
        self.scroll_area = QScrollArea(self.component_center)
        self.scroll_area.setStyleSheet(u"background: transparent;")
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.contents = QWidget()
        self.contents.setGeometry(QRect(0, 0, 840, 580))
        self.contents.setStyleSheet(u"background: transparent;")
        self.verticalLayout = QVBoxLayout(self.contents)
        self.verticalLayout.setSpacing(15)
        self.verticalLayout.setContentsMargins(5, 5, 5, 5)
        self.title_label = QLabel(self.contents)
        self.title_label.setText(QCoreApplication.translate("MainPages", u"Custom Widgets Page", None))

        self.title_label.setMaximumSize(QSize(16777215, 40))
        font = QFont()
        font.setPointSize(16)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet(u"font-size: 16pt")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.verticalLayout.addWidget(self.title_label)
        self.description_label = QLabel(self.contents)
        self.description_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.description_label.setText(QCoreApplication.translate("MainPages",
                                                                  u"Here will be all the custom widgets, they will be added over time on this page.\n"
                                                                  "I will try to always record a new tutorial when adding a new Widget and updating the project on Patreon before launching on GitHub and GitHub after the public release.",
                                                                  None))
        self.description_label.setWordWrap(True)
        self.verticalLayout.addWidget(self.description_label)
        self.row_1_layout = QHBoxLayout()
        self.verticalLayout.addLayout(self.row_1_layout)
        self.row_2_layout = QHBoxLayout()
        self.verticalLayout.addLayout(self.row_2_layout)
        self.row_3_layout = QHBoxLayout()
        self.verticalLayout.addLayout(self.row_3_layout)
        self.row_4_layout = QVBoxLayout()
        self.verticalLayout.addLayout(self.row_4_layout)
        self.row_5_layout = QVBoxLayout()
        self.verticalLayout.addLayout(self.row_5_layout)
        self.scroll_area.setWidget(self.contents)
        self.page_2_layout.addWidget(self.scroll_area)
        self.pages.addWidget(self.component_center)
        self.main_pages_layout.addWidget(self.pages)

        self.pages.setCurrentIndex(0)
        QMetaObject.connectSlotsByName(main_window)

    def load_data(self):
        # 模拟延迟加载数据
        QTimer.singleShot(3000, self.show_data)  # 3秒后调用show_data方法

    def show_data(self):
        self.label.setText(self.text)
