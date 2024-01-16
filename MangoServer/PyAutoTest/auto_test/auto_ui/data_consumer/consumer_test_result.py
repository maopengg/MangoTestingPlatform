# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
import logging

from PyAutoTest.auto_test.auto_ui.models import UiPageSteps, UiCase, UiCaseStepsDetailed
from PyAutoTest.auto_test.auto_ui.views.ui_case_result import UiCaseResultSerializers
from PyAutoTest.auto_test.auto_ui.views.ui_ele_result import UiEleResultSerializers
from PyAutoTest.auto_test.auto_ui.views.ui_page_steps_result import UiPageStepsResultSerializers
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.models.socket_model.ui_model import CaseResultModel, PageStepsResultModel, ElementResultModel

log = logging.getLogger('ui')


class ConsumerTestResult:

    @classmethod
    def page_step_status_update(cls, data: PageStepsResultModel) -> None:
        try:
            res = UiPageSteps.objects.get(id=data.page_step_id)
            res.type = StatusEnum.SUCCESS.value if data.status else StatusEnum.FAIL.value
            res.save()
        except UiPageSteps.DoesNotExist as e:
            # 处理找不到对应记录的情况
            log.error(f"当前查询结果是空，请检查id是否在数据库中存在id：{data.page_step_id}报错：{e}")

    @classmethod
    def update_case_status(cls, case_id: int, status: int, ):
        case = UiCase.objects.get(id=case_id)
        case.status = status
        case.save()

    @classmethod
    def update_case_result(cls, data: CaseResultModel, error_message: str = None):
        for i in data.case_res_list:
            cls.update_page_steps(i, error_message)
        serializer = UiCaseResultSerializers(data=data.dict())
        if serializer.is_valid():
            serializer.save()
        else:
            log.error(f'增加用例结果，请联系管理员进行查看，错误信息：{serializer.errors}')

    @classmethod
    def update_page_steps(cls, data: PageStepsResultModel, error_message: str):
        for i in data.ele_result_list:
            cls.update_ele(i, error_message)
        serializer = UiPageStepsResultSerializers(data=data.dict())
        if serializer.is_valid():
            serializer.save()
        else:
            log.error(f'增加用例步骤结果，请联系管理员进行查看，错误信息：{serializer.errors}')

    @classmethod
    def update_ele(cls, data: ElementResultModel, error_message: str):
        serializer = UiEleResultSerializers(data=data.dict())
        if serializer.is_valid():
            serializer.save()
        else:
            log.error(f'增加元素结果，请联系管理员进行查看，错误信息：{serializer.errors}')
        if data.status == StatusEnum.SUCCESS.value:
            error_message = None
        cls.update_case_detailed(data.case_step_details_id, data.status, error_message)

    @classmethod
    def update_case_detailed(cls, case_step_detailed_id: int, status: int, error_message: str):
        case_step_detailed_dict = UiCaseStepsDetailed.objects.get(id=case_step_detailed_id)
        case_step_detailed_dict.status = status
        case_step_detailed_dict.error_message = error_message
        case_step_detailed_dict.save()
