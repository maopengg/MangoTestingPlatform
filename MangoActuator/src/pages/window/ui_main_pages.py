# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description:
# @Time   : 2024-08-16 17:05
# @Author : 毛鹏
from PySide6.QtCore import QMetaObject
from PySide6.QtWidgets import QVBoxLayout, QStackedWidget

from src.pages.component.component_center import ComponentPage
from src.pages.example import ExamplePage
from src.pages.home.home import HomePage
from src.pages.ui_test import *
from src.pages.web import WebPage


class MainPages:

    def __init__(self, central_widget):
        self.central_widget = central_widget

    def setup_ui(self, main_window):
        self.main_pages_layout = QVBoxLayout(main_window)
        self.main_pages_layout.setSpacing(0)
        self.main_pages_layout.setContentsMargins(0, 0, 0, 0)
        self.pages = QStackedWidget(main_window)
        self.main_pages_layout.addWidget(self.pages)

        self.page_dict = {
            'home': HomePage(),
            'web': WebPage('http://121.37.174.56:8001/'),

            'page': PagePage(self),
            'page_element': ElementPage(self),
            'page_steps': PageStepsPage(self),
            'page_steps_detailed': PageStepsDetailedPage(self),
            'case': CasePage(self),
            'case_steps': CaseStepsPage(self),

            'component_center': ComponentPage(self.central_widget),
            'settings': ExamplePage('设置'),
            'user': ExamplePage('用户'),
        }
        for page in self.page_dict.values():
            self.pages.addWidget(page)

        self.pages.setCurrentIndex(0)
        QMetaObject.connectSlotsByName(main_window)

    def set_page(self, page, data: dict | None = None):
        if isinstance(page, str) and data is not None:
            page = self.page_dict.get(page)
            if isinstance(data, dict):
                page.data = data
            else:
                page.data = {}
        try:
            page.show_data()
        except AttributeError:
            pass
        self.pages.setCurrentWidget(page)
