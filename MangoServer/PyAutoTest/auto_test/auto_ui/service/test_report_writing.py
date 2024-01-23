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
from PyAutoTest.models.socket_model.ui_model import CaseResultModel, PageStepsResultModel

log = logging.getLogger('ui')


class TestReportWriting:

    @classmethod
    def update_page_step_status(cls, data: PageStepsResultModel) -> None:
        """
        步骤状态修改
        @param data:
        @return:
        """
        res = UiPageSteps.objects.get(id=data.page_step_id)
        res.type = data.status
        res.save()

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
            # 更新测试报告页面的状态和错误提示语
            case_step_detailed_dict = UiCaseStepsDetailed.objects.get(id=page_steps_result.case_step_details_id)
            case_step_detailed_dict.status = page_steps_result.status
            if page_steps_result.status == StatusEnum.FAIL.value:
                case_step_detailed_dict.error_message = page_steps_result.error_message
                # error_message.append(page_steps_result.error_message)
            case_step_detailed_dict.save()
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
        # if data.is_batch == StatusEnum.SUCCESS.value:
        #     TestSuiteReportUpdate.update_case_suite_status(data.test_suite_id,
        #                                                    data.status,
        #                                                    StatusEnum.SUCCESS.value,
        #                                                    error_message
        #                                                    )
