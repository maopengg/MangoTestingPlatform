# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-12-11 16:24
# @Author : 毛鹏
from src.auto_test.auto_system.consumers import ChatConsumer
from src.auto_test.auto_system.models import TasksDetails, Tasks
from src.enums.socket_api_enum import UiSocketEnum
from src.enums.system_enum import ClientTypeEnum, ClientNameEnum
from src.models.socket_model import SocketDataModel, QueueModel
from src.models.system_model import CmdTestModel


class CmdTest:
    def __init__(self,
                 user_id: int,
                 username: str,
                 test_env: int,
                 tasks_id: int,
                 is_notice: int = 0,
                 is_send: bool = False):
        self.user_id = user_id
        self.username = username
        self.test_env = test_env
        self.tasks_id = tasks_id
        self.is_notice = is_notice
        self.is_send = is_send
        self.tasks = Tasks.objects.get(id=tasks_id)

    def test_case(self,
                  test_suite: int,
                  test_suite_details: int):
        tasks_details = TasksDetails.objects.filter(task_id=self.tasks_id)
        cmd = []
        for i in tasks_details:
            cmd.append(i.command)
        data_model = CmdTestModel(
            test_suite_details=test_suite_details,
            test_suite_id=test_suite,
            username=self.username,
            project_product=self.tasks.project_product.id,
            project_product_name=self.tasks.project_product.name,
            test_env=self.test_env,
            cmd=cmd
        )
        self.__socket_send(data_model, UiSocketEnum.MangoPytest.value)

    def __socket_send(self, data_model, func_name: str) -> None:
        if self.is_send:
            data = QueueModel(func_name=func_name, func_args=data_model)
            ChatConsumer.active_send(SocketDataModel(
                code=200,
                msg=f'{ClientNameEnum.DRIVER.value}：收到用例数据，准备开始执行自动化任务！',
                user=self.username,
                is_notice=ClientTypeEnum.ACTUATOR.value,
                data=data,
            ))
