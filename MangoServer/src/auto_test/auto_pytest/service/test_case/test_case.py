# -*- coding: utf-8 -*-
# @Project: 
# @Description: 
# @Time   : 2025-02-22 下午4:34
# @Author : 毛鹏
import os
import random
import subprocess
import uuid

from src.auto_test.auto_pytest.models import PytestCase
from src.auto_test.auto_system.consumers import ChatConsumer
from src.auto_test.auto_system.service.socket_link.socket_user import SocketUser
from src.enums.pytest_enum import PytestSystemEnum
from src.enums.system_enum import ClientNameEnum, ClientTypeEnum
from src.enums.tools_enum import TaskEnum
from src.exceptions import MangoServerError
from src.models.pytest_model import PytestCaseModel
from src.models.socket_model import SocketDataModel, QueueModel
from src.tools import project_dir
from src.tools.log_collector import log


class TestCase:

    def __init__(self, user_id=None, test_suite=None, test_suite_details=None):
        self.user_id = user_id
        self.test_suite = test_suite
        self.test_suite_details = test_suite_details

    def test_case_main(self, case_id, test_env: int) -> list[dict]:
        obj: PytestCase = PytestCase.objects.get(id=case_id)
        obj.status = TaskEnum.PROCEED.value
        obj.save()
        PytestCaseModel(
            send_user=self.user_id,
            test_suite_details=self.test_suite_details,
            test_suite_id=self.test_suite,
            id=obj.id,
            name=obj.name,
            project_product=obj.project_product.project_product.id,
            project_product_name=obj.project_product.project_product.name,
            module_name=obj.module.name,
            test_env=test_env,
            case_people=obj.case_people.name,
            file_path='',
        )

        return report_data

    def __socket_send(self, data_model: PytestCaseModel, func_name: str, is_open=False) -> None:
        if self.is_send:
            send_data = SocketDataModel(
                code=200,
                msg=f'{ClientNameEnum.DRIVER.value}：收到用例数据，准备开始执行自动化任务！',
                user=self.user_id,
                is_notice=ClientTypeEnum.ACTUATOR,
                data=QueueModel(func_name=func_name, func_args=data_model),
            )
            try:
                ChatConsumer.active_send(send_data)
            except MangoServerError as error:
                user_list = [i.username for i in SocketUser.user if i.is_open]
                if error.code == 1028 and is_open and user_list:
                    send_data.user = user_list[random.randint(0, len(user_list) - 1)]
                    ChatConsumer.active_send(send_data)
                else:
                    raise error
