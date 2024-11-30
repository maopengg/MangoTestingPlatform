# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-23 22:49
# @Author : 毛鹏
from datetime import timedelta

import time
from django.utils import timezone

from PyAutoTest.auto_test.auto_api.service.api_call.case_flow import CaseFlow
from PyAutoTest.auto_test.auto_system.models import TestSuiteDetails, TestSuite
from PyAutoTest.auto_test.auto_ui.service.send_test_data import SendTestData
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.enums.tools_enum import TaskEnum
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.models.api_model import ApiCaseModel
from PyAutoTest.tools.log_collector import log


class ConsumerThread:
    def __init__(self):
        self.running = True

    def stop(self):
        self.running = False

    def consumer(self):
        reset_tims = time.time()
        while self.running:
            test_suite_details = TestSuiteDetails.objects.filter(
                status=TaskEnum.STAY_BEGIN.value,
                retry__lte=3
            ).first()
            if test_suite_details:
                test_suite = TestSuite.objects.get(id=test_suite_details.test_suite.id)
                if test_suite_details.type == AutoTestTypeEnum.UI.value:
                    try:
                        SendTestData(
                            user_id=test_suite.user.id,
                            test_env=test_suite_details.test_env,
                            tasks_id=test_suite.id,
                            is_notice=test_suite.is_notice,
                            is_send=True
                        ).test_case(case_id=test_suite_details.case_id, test_suite=test_suite_details.test_suite.id,
                                    test_suite_details=test_suite_details.id)
                        log.system.info(
                            f'推送UI任务成功，用例数据：{{"case_id":{test_suite_details.case_id},"test_suite":{test_suite_details.test_suite.id},"test_suite_details":{test_suite_details.id}}}')
                    except MangoServerError as error:
                        test_suite_details.status = TaskEnum.FAIL.value
                        test_suite_details.error_message = f'发送未知异常，请联系管理员处理，异常内容：{error}'
                    else:
                        test_suite_details.status = TaskEnum.PROCEED.value

                elif test_suite_details.type == AutoTestTypeEnum.API.value:
                    api_case_model = ApiCaseModel(
                        test_suite_details=test_suite_details.id,
                        test_suite=test_suite_details.test_suite.id,
                        case_id=test_suite_details.case_id,
                        test_env=test_suite_details.test_env,
                        user_id=test_suite.user.id,
                        tasks_id=test_suite.tasks.id if test_suite.tasks else None,
                    )
                    CaseFlow().add_task(api_case_model)
                    log.system.info(f"推送API任务成功，用例数据：{api_case_model.model_dump_json()}")
                    test_suite_details.status = TaskEnum.PROCEED.value

                test_suite_details.retry += 1
                test_suite_details.push_time = timezone.now()
                test_suite_details.save()

            if time.time() - reset_tims > 1 * 60:
                reset_tims = time.time()
                test_suite_details_list = TestSuiteDetails.objects.filter(
                    status=TaskEnum.PROCEED.value,
                    retry__lt=3
                )
                for test_suite_detail in test_suite_details_list:
                    if test_suite_detail.push_time and (
                            timezone.now() - test_suite_detail.push_time > timedelta(minutes=1)):
                        test_suite_detail.status = TaskEnum.STAY_BEGIN.value
                        test_suite_detail.save()
                        log.system.info(f'推送时间超过30分钟，状态已重置为：待执行，用例ID：{test_suite_detail.case_id}')
                test_suite_details_list = TestSuiteDetails.objects.filter(
                    status=TaskEnum.PROCEED.value,
                    retry=3
                )
                for test_suite_detail in test_suite_details_list:
                    if test_suite_detail.push_time and (
                            timezone.now() - test_suite_detail.push_time > timedelta(minutes=1)):
                        test_suite_detail.status = TaskEnum.FAIL.value
                        test_suite_detail.save()
                        log.system.info(f'连续3次都是待执行，状态直接设置为：失败，用例ID：{test_suite_detail.case_id}')
