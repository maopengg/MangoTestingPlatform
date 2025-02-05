# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-23 22:49
# @Author : 毛鹏
import traceback
from datetime import timedelta

import time
from django.db import connection, close_old_connections
from django.db.utils import Error
from django.utils import timezone

from src.auto_test.auto_api.service.api_call.case_flow import CaseFlow
from src.auto_test.auto_system.models import TestSuiteDetails, TestSuite
from src.auto_test.auto_system.service.cmd_test import CmdTest
from src.auto_test.auto_system.service.socket_link.socket_user import SocketUser
from src.auto_test.auto_ui.service.send_test_data import SendTestData
from src.enums.tools_enum import TaskEnum, AutoTestTypeEnum
from src.exceptions import MangoServerError
from src.models.api_model import ApiCaseModel
from src.settings import IS_SEND_MAIL
from src.tools.log_collector import log
from mangokit import Mango


class ConsumerThread:
    def __init__(self):
        self.running = True
        self.clean_time = 1  # 每隔1分钟，就检查一次全部数据是否有可以回写的状态
        self.reset_time = 10  # 执行中超过10分钟的用例，会被重新设置为待执行
        self.consumer_sleep = 1  # 每次循环等待1秒
        self.retry_frequency = 3  # 重试次数
        self.current_index = 0
        self.environment_error_mix = 10  # 寻找用户测试的时候，最大次数,会*3

    def stop(self):
        self.running = False

    def consumer(self):
        reset_tims = time.time()
        while self.running:
            try:
                test_suite_details = TestSuiteDetails.objects.filter(
                    status=TaskEnum.STAY_BEGIN.value,
                    retry__lt=self.retry_frequency
                ).first()
                if test_suite_details:
                    test_suite = TestSuite.objects.get(id=test_suite_details.test_suite.id)
                    if test_suite_details.type == AutoTestTypeEnum.UI.value:
                        self.ui(0, test_suite, test_suite_details)
                    elif test_suite_details.type == AutoTestTypeEnum.API.value:
                        self.api(test_suite, test_suite_details)
                    elif test_suite_details.type == AutoTestTypeEnum.MangoPytest.value:
                        self.mango_pytest(test_suite, test_suite_details)
                    test_suite_details.retry += 1
                    test_suite_details.push_time = timezone.now()
                    test_suite_details.save()

                if time.time() - reset_tims > self.clean_time * 60:
                    reset_tims = time.time()
                    self.clean_proceed()
                    self.clean_proceed_set_fail()
                time.sleep(self.consumer_sleep)
            except Error:
                close_old_connections()
                connection.ensure_connection()
            except Exception as error:
                log.system.error(error)
                trace = traceback.format_exc()
                if IS_SEND_MAIL:
                    Mango.s(self.consumer, error, trace, )

    def ui(self, environment_error, test_suite, test_suite_details):
        try:
            user_list = SocketUser.user
            if not user_list:
                log.system.warning('用户列表为空，无法发送任务，请先保持至少一个执行器是登录状态~')
                return
            try:
                self.current_index = (self.current_index + 1) % len(user_list)
                user = user_list[self.current_index]
            except IndexError:
                return self.ui(environment_error, test_suite, test_suite_details)
            send_case = SendTestData(
                user_id=user.user_id,
                username=user.username,
                test_env=test_suite_details.test_env,
                tasks_id=test_suite.tasks.id if test_suite.tasks else None,
                is_notice=test_suite.is_notice,
                is_send=True
            )
            inspect = send_case.inspect_environment_config(test_suite_details.case_id)
            environment_error += 1
            if not inspect:
                if environment_error > self.environment_error_mix:
                    test_suite.status = TaskEnum.FAIL.value
                    test_suite.save()
                    test_suite_details.status = TaskEnum.FAIL.value
                    test_suite_details.error_message = f'你配置了不同UI自动化类型，但是你没有准备好UI设备配置，请先前往界面自动化->设备配置中添加配置！'
                    test_suite.save()
                else:
                    time.sleep(2)
                    return self.ui(environment_error, test_suite, test_suite_details)
            else:
                send_case.test_case(
                    case_id=test_suite_details.case_id,
                    test_suite=test_suite_details.test_suite.id,
                    test_suite_details=test_suite_details.id
                )
                log.system.info(
                    f'推送UI任务成功，数据：{{"case_id":{test_suite_details.case_id},"test_suite":{test_suite_details.test_suite.id},"test_suite_details":{test_suite_details.id}}}')
                self.update_status_proceed(test_suite, test_suite_details)

        except MangoServerError as error:
            log.system.warning(f'UI测试任务发生已知错误，忽略错误，等待重新开始：{error.msg}')
        except Exception as error:
            self.error(test_suite, test_suite_details, error, traceback.format_exc())

    def api(self, test_suite, test_suite_details):
        try:
            api_case_model = ApiCaseModel(
                test_suite_details=test_suite_details.id,
                test_suite=test_suite_details.test_suite.id,
                case_id=test_suite_details.case_id,
                test_env=test_suite_details.test_env,
                user_id=test_suite.user.id,
                tasks_id=test_suite.tasks.id if test_suite.tasks else None,
            )
            CaseFlow().add_task(api_case_model)
            log.system.info(
                f'推送API任务成功，数据：{{"case_id":{test_suite_details.case_id},"test_suite":{test_suite_details.test_suite.id},"test_suite_details":{test_suite_details.id}}}')
            self.update_status_proceed(test_suite, test_suite_details)
        except MangoServerError as error:
            log.system.warning(f'API测试任务发生已知错误，忽略错误，等待重新开始：{error.msg}')
        except Exception as error:
            self.error(test_suite, test_suite_details, error, traceback.format_exc())

    def mango_pytest(self, test_suite, test_suite_details):
        try:
            send_case = CmdTest(
                user_id=test_suite.user.id,
                username=test_suite.user.username,
                test_env=test_suite_details.test_env,
                tasks_id=test_suite.tasks.id,
                is_notice=test_suite.is_notice,
                is_send=True
            )
            send_case.test_case(
                test_suite=test_suite_details.test_suite.id,
                test_suite_details=test_suite_details.id
            )
            log.system.info(
                f'推送UI任务成功，数据：{{"case_id":{test_suite_details.case_id},"test_suite":{test_suite_details.test_suite.id},"test_suite_details":{test_suite_details.id}}}')
            self.update_status_proceed(test_suite, test_suite_details)
        except MangoServerError as error:
            log.system.warning(f'UI测试任务发生已知错误，忽略错误，等待重新开始：{error.msg}')
        except Exception as error:
            self.error(test_suite, test_suite_details, error, traceback.format_exc())

    def clean_proceed(self):
        """
        把进行中的，修改为待开始
        """
        test_suite_details_list = TestSuiteDetails \
            .objects \
            .filter(status=TaskEnum.PROCEED.value, retry__lt=self.retry_frequency)
        for test_suite_detail in test_suite_details_list:
            if test_suite_detail.push_time and (
                    timezone.now() - test_suite_detail.push_time > timedelta(minutes=self.reset_time)):
                test_suite_detail.status = TaskEnum.STAY_BEGIN.value
                test_suite_detail.save()
                log.system.info(f'推送时间超过30分钟，状态已重置为：待执行，用例ID：{test_suite_detail.case_id}')

    def clean_proceed_set_fail(self):
        """
        把重试次数满的，修改为0，只有未知错误才会设置为失败
        """
        test_suite_details_list = TestSuiteDetails \
            .objects \
            .filter(status=TaskEnum.STAY_BEGIN.value, retry=self.retry_frequency)
        for test_suite_detail in test_suite_details_list:
            if test_suite_detail \
                    .push_time and (timezone.now() - test_suite_detail.push_time > timedelta(minutes=self.reset_time)):
                test_suite_detail.retry = 0
                test_suite_detail.save()
                log.system.info(f'连续3次都是待执行，重新把重试次数设置为0，用例ID：{test_suite_detail.case_id}')

    def update_status_proceed(self, test_suite, test_suite_details):
        test_suite.status = TaskEnum.PROCEED.value
        test_suite.save()
        test_suite_details.status = TaskEnum.PROCEED.value
        test_suite_details.save()

    def error(self, test_suite, test_suite_details, error, trace):
        test_suite.status = TaskEnum.FAIL.value
        test_suite.save()
        test_suite_details.status = TaskEnum.FAIL.value
        test_suite_details.error_message = f'发生未知异常，请联系管理员处理，类型：{AutoTestTypeEnum.get_value(test_suite.type)}，异常内容：{error}'
        test_suite.save()
        from mangokit import Mango
        log.api.error(f'API执行报错：{trace}')
        Mango.s(self.error, error, trace)
