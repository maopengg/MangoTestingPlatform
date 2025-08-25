# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-11 10:53
# @Author : 毛鹏
import asyncio
import threading

from PySide6.QtCore import QThread, Signal, QTimer
from mangoui import warning_notification, error_notification, success_notification, info_notification, \
    MangoMain1Window, AppConfig, MenusModel

from src import process, log
from ...enums.gui_enum import TipsTypeEnum
from ...models import queue_notification
from ...settings.settings import SETTINGS, MENUS


class NotificationTask(QThread):
    notify_signal = Signal(int, str)

    def run(self):
        timer = QTimer()
        timer.timeout.connect(self.check_queue)
        timer.start(100)
        self.exec()

    def check_queue(self):
        while not queue_notification.empty():
            data: dict = queue_notification.get_nowait()
            self.notify_signal.emit(data['type'].value, data['value'])


class WindowLogic(MangoMain1Window):
    def __init__(self, loop):
        from ..home import HomePage
        from ..setting import SettingPage
        from ..user import UserPage
        from ..ui import AndroidPage, PcPage, WEBPage
        from ..pytest import PytestPage

        page_dict = {
            'home': HomePage,
            'settings': SettingPage,
            'web': WEBPage,
            'android': AndroidPage,
            'pc': PcPage,
            'pytest': PytestPage,
            'user': UserPage,
        }
        super().__init__(
            AppConfig(**SETTINGS),
            MenusModel(**MENUS),
            page_dict,
            loop,
            page='home',
            width_coefficient=0.55,
            height_coefficient=0.65
        )
        self.loop = loop

        def run_process():
            try:
                # 使用已有的self.loop而不是创建新的事件循环
                asyncio.run_coroutine_threadsafe(process(self), self.loop)
            except Exception as e:
                import traceback
                traceback.print_exc()
                log.error(f"运行process协程时出现异常: {e}")

        threading.Thread(
            target=run_process,
            daemon=True
        ).start()

        self.notification_thread = NotificationTask()
        self.notification_thread.notify_signal.connect(self.handle_notification)
        self.notification_thread.start()

    def handle_notification(self, notification_type, message):
        if notification_type == TipsTypeEnum.ERROR.value:
            error_notification(self.content_area_frame, message)
        elif notification_type == TipsTypeEnum.SUCCESS.value:
            success_notification(self.content_area_frame, message)
        elif notification_type == TipsTypeEnum.INFO.value:
            info_notification(self.content_area_frame, message)
        elif notification_type == TipsTypeEnum.WARNING.value:
            warning_notification(self.content_area_frame, message)

    def set_tips_info(self, mag: str):
        self.credits.update_label.emit(str(mag))
