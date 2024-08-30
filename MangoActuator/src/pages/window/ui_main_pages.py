from PySide6.QtCore import QMetaObject
from PySide6.QtWidgets import QVBoxLayout, QStackedWidget

from src.pages.component.component_center import ComponentPage
from src.pages.example import ExamplePage
from src.pages.home.home import HomePage
from src.pages.ui_test.page import PagePage
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

        self.page_dict = [
            HomePage(),
            PagePage(),
            ExamplePage('设置'),
            ExamplePage('用户'),
            WebPage('http://121.37.174.56:8001/'),
            ComponentPage(self.central_widget)
        ]
        for page in self.page_dict:
            self.pages.addWidget(page)

        self.pages.setCurrentIndex(0)
        QMetaObject.connectSlotsByName(main_window)
