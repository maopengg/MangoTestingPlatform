# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
import logging

from PyAutoTest.auto_test.auto_system.service.update_test_suite import TestSuiteReportUpdate
from PyAutoTest.auto_test.auto_ui.models import UiPageSteps, UiCase, UiCaseStepsDetailed
from PyAutoTest.auto_test.auto_ui.views.ui_case_result import UiCaseResultSerializers
from PyAutoTest.auto_test.auto_ui.views.ui_ele_result import UiEleResultSerializers
from PyAutoTest.auto_test.auto_ui.views.ui_page_steps_result import UiPageStepsResultSerializers
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.exceptions.tools_exception import DoesNotExistError
from PyAutoTest.models.socket_model.ui_model import CaseResultModel, PageStepsResultModel
from PyAutoTest.tools.view_utils.error_msg import ERROR_MSG_0030

log = logging.getLogger('ui')


class TestReportWriting:

    @classmethod
    def update_page_step_status(cls, data: PageStepsResultModel) -> None:
        """
        步骤状态修改
        @param data:
        @return:
        """
        try:
            if data.page_step_id:
                res = UiPageSteps.objects.get(id=data.page_step_id)
                res.type = data.status
                res.save()
        except UiPageSteps.DoesNotExist as error:
            raise DoesNotExistError(*ERROR_MSG_0030, error=error)

    @classmethod
    def update_case(cls, data: CaseResultModel):
        """
        用例状态修改
        @param data:CaseResultModel
        @return:
        """
        case = UiCase.objects.get(id=data.case_id)
        case.status = data.status
        case.test_suite_id = data.test_suite_id
        case.save()
        # 保存用例结果
        # error_message = []
        for page_steps_result in data.page_steps_result_list:
            # 保存测试步骤结果
            serializer = UiPageStepsResultSerializers(data=page_steps_result.dict())
            if serializer.is_valid():
                serializer.save()
            else:
                log.error(f'增加用例步骤结果，请联系管理员进行查看，错误信息：{serializer.errors}')
            cls.update_step(page_steps_result)
            for element_result in page_steps_result.element_result_list:
                # 保存元素测试结果
                serializer = UiEleResultSerializers(data=element_result.dict())
                if serializer.is_valid():
                    serializer.save()
                else:
                    log.error(f'增加元素结果，请联系管理员进行查看，错误信息：{serializer.errors}')

        case_result_serializer = UiCaseResultSerializers(data=data.dict())
        if case_result_serializer.is_valid():
            case_result_serializer.save()
        else:
            log.error(f'增加用例结果，请联系管理员进行查看，错误信息：{case_result_serializer.errors}')

    @classmethod
    def update_step(cls, step_data: PageStepsResultModel):
        case_step_detailed = UiCaseStepsDetailed.objects.get(id=step_data.case_step_details_id)
        case_step_detailed.status = step_data.status
        case_step_detailed.error_message = step_data.error_message
        case_step_detailed.save()
        #
        page_step = UiPageSteps.objects.get(id=step_data.page_step_id)
        page_step.type = step_data.status
        page_step.save()
