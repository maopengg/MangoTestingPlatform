# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-11 10:53
# @Author : 毛鹏
import asyncio
import threading

from PySide6.QtCore import QThread, Signal, QTimer
from mangoui import warning_notification, error_notification, success_notification, info_notification, \
    MangoMain1Window, DialogWidget, FormDataModel

from src import process
from src.enums.tools_enum import EnvironmentEnum
from src.network import HTTP
from src.settings import settings
from src.settings.settings import STYLE, MENUS
from ...enums.gui_enum import TipsTypeEnum
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
            self.notify_signal.emit(data['type'].value, data['value'])


class WindowLogic(MangoMain1Window):
    def __init__(self, loop):
        from ..tools import SmallToolsPage
        if settings.IS_NEW:
            from ..home2 import HomePage
            from ..ui_settings import SettingPage
            page_dict = {
                'home': HomePage,
                'ui_settings': SettingPage,
                'tools': SmallToolsPage,
            }
        else:
            from src.pages.api import ApiCasePage, ApiInfoPage, ApiHeadersPage, ApiPublicPage, ApiInfoDetailedPage, \
                ApiCaseDetailedPage
            from ..config import EnvConfigPage, ProductPage, ProjectPage, ModulePage, TestEnvPage, TestFilePage
            from ..home import HomePage
            from ..report import TestSuitePage, TestSuiteDetailedPage
            from ..setting import SettingPage, RolePage, UserLogPage, UserAdministrationPage
            from ..tasks import TasksPage, TasksDetailsPage, TimePage
            from ..ui import PagePage, PublicPage, PageStepsPage, PageStepsDetailedPage, CasePage, ElementPage, \
                CaseStepsPage, EquipmentPage
            from ..user import UserPage

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
                'api_headers': ApiHeadersPage,

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
                print(f"运行process协程时出现异常: {e}")

        threading.Thread(
            target=run_process,
            daemon=True
        ).start()

        self.notification_thread = NotificationTask()
        self.notification_thread.notify_signal.connect(self.handle_notification)
        self.notification_thread.start()

        self.clicked.connect(self.title_bar_clicked_func)

    def handle_notification(self, notification_type, message):
        if notification_type == TipsTypeEnum.ERROR.value:
            error_notification(self.content_area_frame, message)
        elif notification_type == TipsTypeEnum.SUCCESS.value:
            success_notification(self.content_area_frame, message)
        elif notification_type == TipsTypeEnum.INFO.value:
            info_notification(self.content_area_frame, message)
        elif notification_type == TipsTypeEnum.WARNING.value:
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
                response: ResponseModel = HTTP.user.info.put_user_project(user_info.id,
                                                                          dialog.data.get('selected_project'))
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
                response: ResponseModel = HTTP.user.info.put_environment(user_info.id,
                                                                         dialog.data.get('selected_environment'))
                response_message(self.central_widget, response)
                if response.code == 200:
                    user_info.selected_project = response.data.get('selected_environment')

    def set_tips_info(self, mag: str):
        self.credits.update_label.emit(str(mag))
