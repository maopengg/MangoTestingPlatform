# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-09-28 15:49
# @Author : 毛鹏
import asyncio

from PySide6.QtCore import QThreadPool, QRunnable, Signal, Slot, QObject
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QMainWindow, QApplication, QSystemTrayIcon, QMenu, QLabel

from desktop.window.window import Window
from models.service_http_model import LoginModel
from service.socket_client import SocketMain
from tools.log_collector import log


class SocketTask(QRunnable):
    def __init__(self, socket):
        super().__init__()
        self.socket = socket

    def run(self):
        try:
            asyncio.run(self.socket.main())
        except Exception as e:
            # 在此处添加错误处理逻辑
            log.error(f"Socket task error: {e}")


class WebSocketThread(QObject):
    finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.socket = SocketMain()
        self.thread_pool = QThreadPool()

    def start(self):
        task = SocketTask(self.socket)
        self.thread_pool.start(task)

    @Slot()
    def stop(self):
        self.socket.cancel_tasks()
        self.thread_pool.waitForDone()
        self.finished.emit()


class MainWindow(QMainWindow, Window):
    def __init__(self):
        super().__init__()
        self.setup()
        self.resize(800, 576)

        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon('"D:\测试文件\测试素材\header.jpg"'))  # 设置托盘图标

        # 创建托盘图标菜单
        tray_menu = QMenu(self)
        show_action = QAction("显示窗口", self)
        exit_action = QAction("退出", self)
        tray_menu.addAction(show_action)
        tray_menu.addAction(exit_action)

        # 将菜单与托盘图标关联
        self.tray_icon.setContextMenu(tray_menu)

        # 连接菜单项的槽函数
        show_action.triggered.connect(self.show)
        exit_action.triggered.connect(self.quit)

        # 显示系统托盘图标
        self.tray_icon.show()
        # 创建并启动WebSocketThread线程

        # 创建并启动WebSocketThread线程
        self.websocket_thread = WebSocketThread(self)
        self.websocket_thread.finished.connect(self.quit)
        self.websocket_thread.start()

    def closeEvent(self, event):
        event.ignore()  # 忽略窗口的关闭事件
        self.hide()  # 隐藏窗口

    def status(self, text):
        self.status_bar = self.statusBar()
        self.status_label = QLabel(text, self)
        self.status_bar.addWidget(self.status_label)

    def quit(self):
        # 停止WebSocket线程
        self.websocket_thread.stop()
        # 退出程序
        QApplication.quit()


if __name__ == "__main__":
    LoginModel(ip='127.0.0.1',
               port='8000',
               nickname='毛鹏',
               username='17798339533',
               password='123456',
               user_id='1',
               token='123')
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
