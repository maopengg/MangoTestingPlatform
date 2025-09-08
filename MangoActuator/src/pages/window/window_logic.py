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
from src.enums.tools_enum import MessageEnum
from ...enums.gui_enum import TipsTypeEnum
from ...models.tools_model import MessageModel
from ...settings.settings import SETTINGS, MENUS
from ...tools.send_global_msg import global_msg_queue


class NotificationTask(QThread):
    notify_signal = Signal(MessageModel)

    def run(self):
        timer = QTimer()
        timer.timeout.connect(self.check_queue)
        timer.start(100)
        self.exec()

    def check_queue(self):
        while not global_msg_queue.empty():
            data: MessageModel = global_msg_queue.get_nowait()
            self.notify_signal.emit(data)


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
            width_coefficient=0.45,
            height_coefficient=0.53
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

    def handle_notification(self, msg_model: MessageModel):
        if msg_model.type == MessageEnum.BOTTOM:
            self.credits.update_label.emit(msg_model.msg)
        elif msg_model.type == MessageEnum.REAL_TIME:
            if hasattr(self.page, 'real_time'):
                self.page.real_time.emit(msg_model.msg)
            else:
                from ..home import fixed_list
                fixed_list.append(msg_model.msg)
        elif msg_model.type == MessageEnum.WS_LINK:
            if hasattr(self.page, 'real_time'):
                self.page.set_link(msg_model.msg)
        elif msg_model.type == MessageEnum.CASE_NAME:
            if hasattr(self.page, 'real_time'):
                self.page.set_case_name(msg_model.msg)
        elif msg_model.type == MessageEnum.NOTIFICATION:
            if msg_model.level == TipsTypeEnum.ERROR:
                error_notification(self.content_area_frame, msg_model.msg)
            elif msg_model.level == TipsTypeEnum.SUCCESS.value:
                success_notification(self.content_area_frame, msg_model.msg)
            elif msg_model.level == TipsTypeEnum.INFO.value:
                info_notification(self.content_area_frame, msg_model.msg)
            elif msg_model.level == TipsTypeEnum.WARNING.value:
                warning_notification(self.content_area_frame, msg_model.msg)
