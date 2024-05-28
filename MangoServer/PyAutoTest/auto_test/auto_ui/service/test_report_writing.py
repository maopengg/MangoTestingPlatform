# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
import json
import logging

from django.db import connection

from PyAutoTest.auto_test.auto_system.models import TestSuiteReport
from PyAutoTest.auto_test.auto_system.service.notic_tools import NoticeMain
from PyAutoTest.auto_test.auto_ui.models import UiPageSteps, UiCase, UiCaseStepsDetailed, UiCaseResult
from PyAutoTest.auto_test.auto_ui.views.ui_case_result import UiCaseResultCRUD
from PyAutoTest.auto_test.auto_ui.views.ui_ele_result import UiEleResultCRUD
from PyAutoTest.auto_test.auto_ui.views.ui_page_steps_result import UiPageStepsResultCRUD
from PyAutoTest.enums.tools_enum import StatusEnum, ClientTypeEnum
from PyAutoTest.exceptions.tools_exception import DoesNotExistError
from PyAutoTest.models.socket_model import SocketDataModel
from PyAutoTest.models.socket_model.ui_model import CaseResultModel, PageStepsResultModel
from PyAutoTest.tools.decorator.retry import orm_retry
from PyAutoTest.tools.view.error_msg import ERROR_MSG_0030

log = logging.getLogger('ui')


class TestReportWriting:

    @classmethod
    @orm_retry('update_page_step_status')
    def update_page_step_status(cls, data: PageStepsResultModel) -> None:
        try:
            if data.page_step_id:
                res = UiPageSteps.objects.get(id=data.page_step_id)
                res.type = data.status
                res.save()
        except UiPageSteps.DoesNotExist as error:
            raise DoesNotExistError(*ERROR_MSG_0030, error=error)

    @classmethod
    @orm_retry('update_case')
    def update_case(cls, data: CaseResultModel):
        connection.ensure_connection()
        case = UiCase.objects.get(id=data.case_id)
        case.status = data.status
        case.test_suite_id = data.test_suite_id
        case.save()
        # 保存用例结果
        for page_steps_result in data.page_steps_result_list:
            UiPageStepsResultCRUD.inside_post(page_steps_result.dict())
            cls.update_step(page_steps_result)
            for element_result in page_steps_result.element_result_list:
                UiEleResultCRUD.inside_post(element_result.dict())

        UiCaseResultCRUD.inside_post(data.dict())
        cls.update_test_suite(data.test_suite_id)

    @classmethod
    @orm_retry('update_step')
    def update_step(cls, step_data: PageStepsResultModel):
        case_step_detailed = UiCaseStepsDetailed.objects.get(id=step_data.case_step_details_id)
        case_step_detailed.status = step_data.status
        case_step_detailed.error_message = step_data.error_message
        case_step_detailed.save()
        #
        page_step = UiPageSteps.objects.get(id=step_data.page_step_id)
        page_step.type = step_data.status
        page_step.save()

    @classmethod
    @orm_retry('update_test_suite')
    def update_test_suite(cls, test_suite_id: int):
        test_suite_obj = TestSuiteReport.objects.get(id=test_suite_id)
        case_id_status = UiCaseResult \
            .objects \
            .filter(test_suite_id=test_suite_id) \
            .values_list('case_id', 'status', 'error_message')
        case_id_list = []
        status_list = []
        error_message_list = []
        for case_id, status, error_message in case_id_status:
            case_id_list.append(case_id)
            status_list.append(status)
            if error_message:
                error_message_list.append(error_message)
        if set(test_suite_obj.case_list) == set(case_id_list):
            test_suite_obj.run_status = StatusEnum.SUCCESS.value
            if StatusEnum.FAIL.value in status_list:
                test_suite_obj.status = StatusEnum.FAIL.value
                code = 300
                msg = f'测试套：{test_suite_id}执行完成，测试结果全部成功，请前往测试报告查询！'
            else:
                code = 200
                msg = f'测试套：{test_suite_id}执行完成，测试结果全部成功，请前往测试报告查询！'
                test_suite_obj.status = StatusEnum.SUCCESS.value
            test_suite_obj.error_message = json.dumps(error_message_list, ensure_ascii=False)
            test_suite_obj.save()
            if test_suite_obj.is_notice:
                NoticeMain.notice_main(test_suite_obj.project_product.project_id, test_suite_id)
            from PyAutoTest.auto_test.auto_system.consumers import ChatConsumer
            ChatConsumer.active_send(SocketDataModel(
                code=code,
                msg=msg,
                user=test_suite_obj.user.username,
                is_notice=ClientTypeEnum.WEB.value,
            ))
