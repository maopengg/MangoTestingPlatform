# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-11 10:53
# @Author : 毛鹏

import asyncio

from PySide6.QtCore import QThread, Signal, QTimer
from mango_ui import warning_notification, error_notification, success_notification, info_notification, \
    MangoMain1Window, DialogWidget, FormDataModel

from src.enums.tools_enum import EnvironmentEnum
from src.network import HTTP
from src.network.web_socket.websocket_client import WebSocketClient
from src.consumer import SocketConsumer
from src.settings.settings import STYLE, MENUS
from ..api import *
from ..config import *
from ..home import *
from ..report import *
from ..setting import *
from ..tasks import *
from ..tools import *
from ..ui import *
from ..user import *
from ...models import queue_notification
from ...models.socket_model import ResponseModel
from ...models.user_model import UserModel
from ...tools.components.message import response_message
from ...tools.methods import Methods


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
            self.notify_signal.emit(data.get('type'), data.get('value'))


class WindowLogic(MangoMain1Window):
    def __init__(self, loop):
        page_dict = {
            'home': HomePage,
            'page': PagePage,
            'page_element': ElementPage,
            'page_steps': PageStepsPage,
            'page_steps_detailed': PageStepsDetailedPage,
            'case': CasePage,
            'case_steps': CaseStepsPage,
            'public': PublicPage,
            'equipment': EquipmentPage,

            'api_info': ApiInfoPage,
            'api_info_detailed': ApiInfoDetailedPage,
            'api_case': ApiCasePage,
            'api_case_detailed': ApiCaseDetailedPage,
            'api_public': ApiPublicPage,

            'test_suite': TestSuitePage,
            'test_suite_detailed': TestSuiteDetailedPage,

            'project': ProjectPage,
            'product': ProductPage,
            'module': ModulePage,
            'test_env': TestEnvPage,
            'env_config': EnvConfigPage,
            'test_file': TestFilePage,

            'user_administration': UserAdministrationPage,
            'role': RolePage,
            'user_log': UserLogPage,

            'time': TimePage,
            'tasks': TasksPage,
            'tasks_details': TasksDetailsPage,

            'tools': SmallToolsPage,
            'settings': SettingPage,
            'user': UserPage,
        }
        super().__init__(
            STYLE,
            MENUS,
            page_dict,
            loop,
            page='home',
            width_coefficient=0.7,
            height_coefficient=0.815
        )
        self.loop = loop

        self.consumer = SocketConsumer(self)

        self.socket: WebSocketClient = WebSocketClient()
        self.socket.parent = self
        asyncio.run_coroutine_threadsafe(self.socket.client_run(), self.loop)

        self.notification_thread = NotificationTask()
        self.notification_thread.notify_signal.connect(self.handle_notification)
        self.notification_thread.start()

        self.clicked.connect(self.title_bar_clicked_func)

    def handle_notification(self, notification_type, message):
        if notification_type == 0:
            error_notification(self.content_area_frame, message)
        elif notification_type == 1:
            success_notification(self.content_area_frame, message)
        elif notification_type == 2:
            info_notification(self.content_area_frame, message)
        elif notification_type == 3:
            warning_notification(self.content_area_frame, message)

    def title_bar_clicked_func(self, data):
        if data == 'project':
            user_info = UserModel()
            project_list = [FormDataModel(
                title='项目名称',
                placeholder='请选择项目进行全局条件过滤',
                key='selected_project',
                type=1,
                select=Methods.get_project_model(),
                value=str(user_info.selected_project)
            )]

            dialog = DialogWidget('选择项目', project_list)
            dialog.exec()
            if dialog.data:
                response: ResponseModel = HTTP.user.info.put_user_project(user_info.id, dialog.data.get('selected_project'))
                response_message(self.central_widget, response)
                if response.code == 200:
                    HTTP.api.info.headers['Project'] = str(dialog.data.get('selected_project'))
                    user_info.selected_project = response.data.get('selected_project')

        elif data == 'test_env':
            user_info = UserModel()
            env_list = [FormDataModel(
                title='测试环境',
                placeholder='请选择测试环境，用例执行与测试环境绑定',
                key='selected_environment',
                type=1,
                select=EnvironmentEnum.get_select(),
                value=str(user_info.selected_environment)
            )]
            dialog = DialogWidget('选择测试环境', env_list)
            dialog.exec()
            if dialog.data:
                user_info.selected_environment = dialog.data.get('selected_environment')
                response: ResponseModel = HTTP.user.info.put_environment(user_info.id, dialog.data.get('selected_environment'))
                response_message(self.central_widget, response)
                if response.code == 200:
                    user_info.selected_project = response.data.get('selected_environment')

    def set_tips_info(self, mag: str):
        self.credits.update_label.emit(str(mag))
