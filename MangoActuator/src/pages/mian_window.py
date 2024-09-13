# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-09-28 15:49
# @Author : 毛鹏
import os

from PySide6.QtGui import *
from PySide6.QtWidgets import *

from src.network.web_socket.sokcet_thread import SocketTask
from src.pages.window.ui_main_window import UIMainWindow
from src.widgets.mango_tooltip_box import show_info_message

os.environ["QT_FONT_DPI"] = "96"


# 4K 'os.environ["QT_SCALE_FACTOR"] = "2"'


class MainWindow(UIMainWindow):

    def __init__(self):
        super().__init__()
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

        self.websocket_thread = SocketTask()
        self.websocket_thread.start()

    def closeEvent(self, event):
        show_info_message('任务不会关闭，如果想要彻底关闭任务请在任务栏中右键进行退出！')
        event.ignore()
        self.hide()

    @classmethod
    def quit(cls):
        QApplication.quit()

    def resizeEvent(self, event):
        self.resize_grips()

    def mousePressEvent(self, event):
        self.drag_pos = QCursor.pos()


if __name__ == '__main__':
    app = QApplication([])
    app.setStyleSheet("* { font-size: 10pt; }")
    window = MainWindow()
    window.show()
    app.exec()
