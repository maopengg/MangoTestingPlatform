# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-09-28 15:49
# @Author : 毛鹏
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QMainWindow, QSystemTrayIcon, QMenu, QApplication

from src.dialogs.tooltip_box import show_info_message
from src.network.sokcet_thread import SocketTask
from src.pages.window.window_logic import Window
from resources.icons.app_rc import *


# pyside6-rcc D:\GitCode\MangoTestingPlatform\MangoActuator\desktop\app_icon.qrc
# -o D:\GitCode\MangoTestingPlatform\MangoActuator\desktop\app_rc.py


class MainWindow(QMainWindow, Window):

    def __init__(self):
        super().__init__()
        self.setup()
        self.setWindowTitle("PySide6 菜单示例")
        self.setGeometry(100, 100, 800, 600)
        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(':/resource/app_icon.png'))  # 设置托盘图标

        # 创建托盘图标菜单
        tray_menu = QMenu(self)
        show_action = QAction(QIcon(':/resource/show_icon.png'), "显示窗口", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        exit_action = QAction(QIcon(':/resource/close_icon.png'), "退出", self)
        exit_action.triggered.connect(self.quit)
        tray_menu.addAction(exit_action)

        # 将菜单与托盘图标关联
        self.tray_icon.setContextMenu(tray_menu)
        # 显示系统托盘图标
        self.tray_icon.show()

        # 创建并启动WebSocketThread线程
        self.websocket_thread = SocketTask(self)
        self.websocket_thread.finished.connect(self.quit)
        self.websocket_thread.start()

    def closeEvent(self, event):
        show_info_message('提示', '任务不会关闭，如果想要彻底关闭任务请在任务栏中右键进行退出！')
        event.ignore()  # 忽略窗口的关闭事件
        self.hide()  # 隐藏窗口

    def quit(self):
        # 退出程序
        QApplication.quit()
