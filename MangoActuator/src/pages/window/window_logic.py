# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-11 10:53
# @Author : 毛鹏

import asyncio
import traceback

from PySide6.QtCore import QThread, Signal, QTimer
from mango_ui import warning_notification, error_notification, success_notification, info_notification

from src.network.web_socket.websocket_client import WebSocketClient
from src.tools.log_collector import log
from .ui_window import UIWindow
from ...models import queue_notification


class SocketTask(QThread):

    def __init__(self):
        super().__init__()
        self.socket: WebSocketClient = WebSocketClient()

    def run(self):
        try:
            asyncio.run(self.socket.client_run())
        except Exception as e:
            traceback.print_exc()
            log.error(f"主任务出现异常：{e}")


class NotificationTask(QThread):
    notify_signal = Signal(int, str)  # 定义信号，类型和消息文本

    def run(self):
        timer = QTimer()
        timer.timeout.connect(self.check_queue)
        timer.start(100)  # 每100毫秒检查一次队列
        self.exec()  # 进入事件循环

    def check_queue(self):
        while not queue_notification.empty():
            data: dict = queue_notification.get_nowait()
            self.notify_signal.emit(data.get('type'), data.get('value'))


class WindowLogic(UIWindow):
    def __init__(self, loop):
        super().__init__(loop)
        self.loop = loop
        self.websocket_thread = SocketTask()
        self.websocket_thread.start()

        self.notification_thread = NotificationTask()
        self.notification_thread.notify_signal.connect(self.handle_notification)
        self.notification_thread.start()

    def handle_notification(self, notification_type, message):
        if notification_type == 0:
            error_notification(self, message)
        elif notification_type == 1:
            success_notification(self, message)
        elif notification_type == 2:
            info_notification(self, message)
        elif notification_type == 3:
            warning_notification(self, message)
