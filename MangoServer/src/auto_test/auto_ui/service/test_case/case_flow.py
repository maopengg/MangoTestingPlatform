# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-23 20:38
# @Author : 毛鹏

import time

from src.auto_test.auto_system.models import TestSuite, TestSuiteDetails
from src.auto_test.auto_system.service.socket_link.socket_user import SocketUser
from src.auto_test.auto_ui.service.test_case.test_case import TestCase
from src.enums.tools_enum import TaskEnum
from src.models.system_model import ConsumerCaseModel
from src.tools.log_collector import log


class UiCaseFlow:
    current_index = 0

    @classmethod
    def execute_task(cls, case_model: ConsumerCaseModel, retry=0, max_retry=3):
        retry += 1
        user_list = [i for i in SocketUser.user if i.client_obj]
        if not user_list:
            log.system.warning('用户列表为空，无法发送任务，请先保持至少一个执行器是登录状态~')
            time.sleep(5)
            return
        try:
            cls.current_index = (cls.current_index + 1) % len(user_list)
            user = user_list[cls.current_index]
        except IndexError:
            time.sleep(3)
            return cls.execute_task(case_model, retry, max_retry)
        send_case = TestCase(
            user_id=user.user_id,
            username=user.username,
            test_env=case_model.test_env,
            tasks_id=case_model.tasks_id,
            is_send=True
        )
        inspect = send_case.inspect_environment_config(case_model.case_id)
        if not inspect:
            if retry > max_retry:
                test_suite = TestSuite.objects.get(id=case_model.test_suite)
                test_suite.status = TaskEnum.FAIL.value
                test_suite.save()
                test_suite_details = TestSuiteDetails.objects.get(id=case_model.test_suite_details)
                test_suite_details.status = TaskEnum.FAIL.value
                test_suite_details.error_message = f'你配置了不同UI自动化类型，但是你没有准备好UI设备配置，请先前往界面自动化->设备配置中添加配置！'
                test_suite.save()
            else:
                time.sleep(3)
                return cls.execute_task(case_model, retry, max_retry)
        else:
            send_case.test_case(
                case_id=case_model.case_id,
                test_suite=case_model.test_suite,
                test_suite_details=case_model.test_suite_details
            )

    @classmethod
    def add_task(cls, case_model: ConsumerCaseModel):
        cls.execute_task(case_model)
