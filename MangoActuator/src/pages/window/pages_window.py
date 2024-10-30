# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-08-16 17:05
# @Author : 毛鹏
from mango_ui import *
from mango_ui.init import QStackedWidget, QApplication, QMetaObject

from ..config import *
from ..home import *
from ..report import *
from ..setting import *
from ..small_tools import *
from ..time_task import *
from ..ui import *
from ..ui.quipment import EquipmentPage
from ..user import *


class PagesWindow:

    def __init__(self, central_widget, loop):
        self.central_widget = central_widget
        self.loop = loop
        self.loading_indicator = self.create_loading_indicator()

    def create_loading_indicator(self):
        loading_indicator = MangoLabel("数据加载中...")
        from PySide6.QtCore import Qt
        loading_indicator.setAlignment(Qt.AlignCenter)
        loading_indicator.setStyleSheet(f"font-size: 16px; color: {THEME.icon_color};")
        return loading_indicator

    def setup_ui(self, main_window):
        self.main_pages_layout = QVBoxLayout(main_window)
        self.main_pages_layout.setSpacing(0)
        self.main_pages_layout.setContentsMargins(0, 0, 0, 0)
        self.pages = QStackedWidget(main_window)
        self.main_pages_layout.addWidget(self.pages)

        self.page_dict = {
            'home': HomePage,
            'page': PagePage,
            'page_element': ElementPage,
            'page_steps': PageStepsPage,
            'page_steps_detailed': PageStepsDetailedPage,
            'case': CasePage,
            'case_steps': CaseStepsPage,
            'public': PublicPage,
            'equipment': EquipmentPage,
            'project': ProjectPage,
            'product': ProductPage,
            'module': ModulePage,
            'test_env': TestEnvPage,
            'env_config': EnvConfigPage,
            'test_file': TestFilePage,
            'user_administration': UserAdministrationPage,
            'user': UserPage,
            'role': RolePage,
            'time_task': TimeTaskPage,
            'task_case': TaskCasePage,
            'user_log': UserLogPage,
            'test_report': TestReportPage,
            'test_report_detailed': TestReportDetailedPage,
            'small_tools': SmallToolsPage,
            'settings': SettingPage,
        }
        self.pages.setCurrentIndex(0)
        QMetaObject.connectSlotsByName(main_window)

    def set_page(self, page: str, data: dict | None = None):
        self.pages.addWidget(self.loading_indicator)
        self.pages.setCurrentWidget(self.loading_indicator)
        QApplication.processEvents()

        page_class = self.page_dict.get(page)
        if page_class is not None:
            page = page_class(self)
        else:
            return
        current_widget = self.pages.currentWidget()
        if current_widget and current_widget != self.loading_indicator:
            self.pages.removeWidget(current_widget)
        if data is not None and isinstance(data, dict):
            page.data = data
        else:
            page.data = {}
        page.show_data()
        self.pages.addWidget(page)
        self.pages.setCurrentWidget(page)
        self.pages.removeWidget(self.loading_indicator)
