# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-23 22:49
# @Author : 毛鹏
import time
import traceback
from datetime import timedelta

from django.db import connection, close_old_connections
from django.db.utils import Error
from django.utils import timezone

from mangokit.mangos import Mango
from src.auto_test.auto_api.service.test_case.case_flow import ApiCaseFlow
from src.auto_test.auto_pytest.service.test_case.case_flow import PytestCaseFlow
from src.auto_test.auto_system.models import TestSuiteDetails, TestSuite, Tasks
from src.enums.tools_enum import TaskEnum, TestCaseTypeEnum
from src.exceptions import MangoServerError
from src.models.system_model import ConsumerCaseModel
from src.settings import IS_SEND_MAIL
from src.tools.log_collector import log


class ConsumerThread:
    def __init__(self):
        self.running = True
        self.clean_time = 1  # 每隔1分钟，就检查一次全部数据是否有可以回写的状态
        self.reset_time = 15  # 执行中超过n分钟的用例，会被重新设置为待执行
        self.consumer_sleep = 1  # 每次循环等待1秒
        self.retry_frequency = 3  # 重试次数

    def stop(self):
        self.running = False

    def consumer(self):
        reset_tims = time.time()
        while self.running:
            time.sleep(self.consumer_sleep)
            try:

                test_suite_details = TestSuiteDetails.objects.filter(
                    status=TaskEnum.STAY_BEGIN.value,
                    retry__lt=self.retry_frequency + 1,
                    type__in=[TestCaseTypeEnum.API.value, TestCaseTypeEnum.PYTEST.value]
                ).first()

                if test_suite_details:
                    test_suite = TestSuite.objects.get(id=test_suite_details.test_suite.id)
                    try:
                        tasks_id = test_suite.tasks.id if test_suite.tasks else None
                    except Tasks.DoesNotExist:
                        tasks_id = None
                    case_model = ConsumerCaseModel(
                        test_suite_details=test_suite_details.id,
                        test_suite=test_suite_details.test_suite.id,
                        case_id=test_suite_details.case_id,
                        case_name=test_suite_details.case_name,
                        test_env=test_suite_details.test_env,
                        user_id=test_suite.user.id,
                        tasks_id=tasks_id,
                        parametrize=test_suite_details.parametrize
                    )
                    self.send_case(test_suite, test_suite_details, case_model)
                    self.update_status_proceed(test_suite, test_suite_details)

                if time.time() - reset_tims > self.clean_time * 60:
                    reset_tims = time.time()
                    self.clean_proceed()
                    self.clean_proceed_set_fail()
                    self.clean_test_suite_status()
            except Error:
                close_old_connections()
                connection.ensure_connection()
            except Exception as error:
                trace = traceback.format_exc()
                log.system.error(f'自动化任务失败：{error}，报错：{trace}')

                if IS_SEND_MAIL:
                    # Mango.s(self.consumer, error, trace, )
                    pass

    def send_case(self, test_suite, test_suite_details, case_model: ConsumerCaseModel, retry=0, max_retry=3):
        retry += 1
        try:
            if test_suite_details.type == TestCaseTypeEnum.UI.value:
                # UiCaseFlow.add_task(case_model)
                pass
            elif test_suite_details.type == TestCaseTypeEnum.API.value:
                ApiCaseFlow.add_task(case_model)
            else:
                PytestCaseFlow.add_task(case_model)
            log.system.info(
                f'推送{TestCaseTypeEnum.get_value(test_suite_details.type)}任务成功，test_suite_details":{test_suite_details.id}')
        except MangoServerError as error:
            log.system.debug(f'UI测试任务发生已知错误，忽略错误，等待重新开始：{error.msg}')
        except Exception as error:
            if retry > max_retry:
                self.consumer_error(test_suite, test_suite_details, error, traceback.format_exc())
                return
            else:
                self.send_case(test_suite, test_suite_details, case_model, retry, max_retry)

    def clean_test_suite_status(self):
        test_suite = TestSuite.objects.filter(status__in=[TaskEnum.PROCEED.value, TaskEnum.STAY_BEGIN.value])
        for i in test_suite:
            status_list = TestSuiteDetails \
                .objects \
                .filter(test_suite=i).values_list('status', flat=True)
            if TaskEnum.STAY_BEGIN.value not in status_list and TaskEnum.PROCEED.value not in status_list:
                if TaskEnum.FAIL.value in status_list:
                    i.status = TaskEnum.FAIL.value
                else:
                    i.status = TaskEnum.SUCCESS.value
                i.save()

    def clean_proceed(self):
        """
        把进行中的，修改为待开始,或者失败
        """
        test_suite_details_list = TestSuiteDetails \
            .objects \
            .filter(status=TaskEnum.PROCEED.value, retry__lt=self.retry_frequency + 1)
        for test_suite_detail in test_suite_details_list:
            if test_suite_detail.push_time and (
                    timezone.now() - test_suite_detail.push_time > timedelta(minutes=self.reset_time)):
                test_suite_detail.status = TaskEnum.STAY_BEGIN.value
                test_suite_detail.save()
                log.system.info(
                    f'推送时间超过{self.reset_time}分钟，状态重置为：待执行，用例ID：{test_suite_detail.case_id}')

    def clean_proceed_set_fail(self):
        """
        把重试次数满的，修改为0，只有未知错误才会设置为失败
        """
        test_suite_details_list = TestSuiteDetails \
            .objects \
            .filter(status__in=[TaskEnum.PROCEED.value, TaskEnum.STAY_BEGIN.value], retry__gte=self.retry_frequency + 1)
        for test_suite_detail in test_suite_details_list:
            if test_suite_detail.push_time and (
                    timezone.now() - test_suite_detail.push_time > timedelta(minutes=self.reset_time)):
                test_suite_detail.status = TaskEnum.FAIL.value
                test_suite_detail.save()
                log.system.info(
                    f'重试次数超过{self.retry_frequency + 1}次的任务状态重置为：失败，用例ID：{test_suite_detail.case_id}')

    def update_status_proceed(self, test_suite, test_suite_details):
        test_suite.status = TaskEnum.PROCEED.value
        test_suite.save()

        test_suite_details.status = TaskEnum.PROCEED.value
        test_suite_details.retry += 1
        test_suite_details.push_time = timezone.now()
        test_suite_details.save()

    def consumer_error(self, test_suite, test_suite_details, error, trace):
        test_suite.status = TaskEnum.FAIL.value
        test_suite.save()
        test_suite_details.status = TaskEnum.FAIL.value
        test_suite_details.error_message = f'测试{TestCaseTypeEnum.get_value(test_suite_details.type)}类型：，异常类型：{error}，报错内容：{trace}'
        test_suite.save()
        if IS_SEND_MAIL:
            Mango.s(self.consumer_error, error, trace)
