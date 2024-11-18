# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-09-28 15:49
# @Author : 毛鹏
import os

from mango_ui import show_info_message
from mango_ui.init import *

from src.pages.window.window_logic import WindowLogic

os.environ["QT_FONT_DPI"] = "96"


# 4K
# os.environ["QT_SCALE_FACTOR"] = "2"


class MainWindow(WindowLogic):

    def __init__(self, loop):
        super().__init__(loop)
        self.loop = loop
        self.drag_pos = None
        self.is_close_tips = True

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.activated.connect(self.open_window)
        self.tray_icon.setIcon(QIcon(':/icons/app_icon.png'))
        tray_menu = QMenu(self)
        show_action = QAction(QIcon(':/icons/show_icon.png'), "显示窗口", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        exit_action = QAction(QIcon(':/icons/close_icon.png'), "退出", self)
        exit_action.triggered.connect(lambda: QApplication.quit())
        tray_menu.addAction(exit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def open_window(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show()
            self.raise_()
            self.activateWindow()

    def closeEvent(self, event):
        if self.is_close_tips:
            self.is_close_tips = False
            show_info_message('测试平台不会退出，想要退出请在右下角右键退出！')
        event.ignore()
        self.hide()
