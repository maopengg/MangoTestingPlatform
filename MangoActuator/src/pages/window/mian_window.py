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
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(':/icons/app_icon.png'))
        tray_menu = QMenu(self)
        show_action = QAction(QIcon(':/icons/show_icon.png'), "显示窗口", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        exit_action = QAction(QIcon(':/icons/close_icon.png'), "退出", self)
        exit_action.triggered.connect(self.quit)
        tray_menu.addAction(exit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def closeEvent(self, event):
        show_info_message('任务不会关闭，如果想要彻底关闭任务请在任务栏中右键进行退出！')
        event.ignore()
        self.hide()

    @classmethod
    def quit(cls):
        QApplication.quit()
