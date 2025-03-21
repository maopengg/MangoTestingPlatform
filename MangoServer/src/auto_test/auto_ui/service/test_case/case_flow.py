# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-23 20:38
# @Author : 毛鹏

import time
from django.utils import timezone

from src.auto_test.auto_system.models import TestSuite, TestSuiteDetails
from src.auto_test.auto_system.service.socket_link.socket_user import SocketUser
from src.auto_test.auto_user.models import User
from src.enums.tools_enum import TaskEnum, TestCaseTypeEnum
from src.models.system_model import ConsumerCaseModel
from src.models.ui_model import GetTaskModel
from src.tools.log_collector import log


class UiCaseFlow:
    current_index = 0
    retry_frequency = 3

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
        cls.send_case(user.user_id, user.username, case_model)

    @classmethod
    def add_task(cls, case_model: ConsumerCaseModel):
        cls.execute_task(case_model)

    @classmethod
    def get_case(cls, data: GetTaskModel):
        model = User.objects.get(username=data.username)
        test_suite_details = TestSuiteDetails.objects.filter(
            status=TaskEnum.STAY_BEGIN.value,
            retry__lt=cls.retry_frequency,
            type=TestCaseTypeEnum.UI.value
        ).first()
        if test_suite_details:
            test_suite = TestSuite.objects.get(id=test_suite_details.test_suite.id)
            case_model = ConsumerCaseModel(
                test_suite_details=test_suite_details.id,
                test_suite=test_suite_details.test_suite.id,
                case_id=test_suite_details.case_id,
                case_name=test_suite_details.case_name,
                test_env=test_suite_details.test_env,
                user_id=test_suite.user.id,
                tasks_id=test_suite.tasks.id if test_suite.tasks else None,
                parametrize=test_suite_details.parametrize,
            )
            cls.send_case(model.id, model.username, case_model)
            cls.update_status_proceed(test_suite, test_suite_details)

    @classmethod
    def update_status_proceed(cls, test_suite, test_suite_details):
        test_suite.status = TaskEnum.PROCEED.value
        test_suite.save()

        test_suite_details.status = TaskEnum.PROCEED.value
        test_suite_details.retry += 1
        test_suite_details.push_time = timezone.now()
        test_suite_details.save()

    @classmethod
    def send_case(cls, user_id, username, case_model):
        from src.auto_test.auto_ui.service.test_case.test_case import TestCase
        send_case = TestCase(
            user_id=user_id,
            username=username,
            test_env=case_model.test_env,
            tasks_id=case_model.tasks_id,
            is_send=True
        )
        inspect = send_case.inspect_environment_config(case_model.case_id)
        if not inspect:
            test_suite = TestSuite.objects.get(id=case_model.test_suite)
            test_suite.status = TaskEnum.FAIL.value
            test_suite.save()
            test_suite_details = TestSuiteDetails.objects.get(id=case_model.test_suite_details)
            test_suite_details.status = TaskEnum.FAIL.value
            test_suite_details.error_message = f'你配置了不同UI自动化类型，但是你没有准备好UI设备配置，请先前往界面自动化->设备配置中添加配置！'
            test_suite.save()
        else:
            send_case.test_case(
                case_id=case_model.case_id,
                case_name=case_model.case_name,
                test_suite=case_model.test_suite,
                test_suite_details=case_model.test_suite_details,
                parametrize=case_model.parametrize
            )
