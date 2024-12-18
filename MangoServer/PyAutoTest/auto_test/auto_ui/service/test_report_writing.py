# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏

from django.db import connection

from PyAutoTest.auto_test.auto_ui.models import PageSteps, UiCase, UiCaseStepsDetailed
from PyAutoTest.exceptions import *
from PyAutoTest.models.ui_model import UiCaseResultModel, PageStepsResultModel
from PyAutoTest.tools.decorator.retry import orm_retry


class TestReportWriting:

    @classmethod
    @orm_retry('update_page_step_status')
    def update_page_step_status(cls, data: PageStepsResultModel) -> None:
        try:
            res = PageSteps.objects.get(id=data.id)
            res.status = data.status
            res.save()
        except PageSteps.DoesNotExist as error:
            raise UiError(*ERROR_MSG_0030, error=error)

    @classmethod
    @orm_retry('update_test_case')
    def update_test_case(cls, data: UiCaseResultModel):
        connection.ensure_connection()
        case = UiCase.objects.get(id=data.id)
        case.status = data.status
        case.save()
        for i in data.steps:
            cls.update_step(i)

    @classmethod
    @orm_retry('update_step')
    def update_step(cls, step_data: PageStepsResultModel):
        case_step_detailed = UiCaseStepsDetailed.objects.get(id=step_data.case_step_details_id)
        case_step_detailed.status = step_data.status
        case_step_detailed.error_message = step_data.error_message
        case_step_detailed.result_data = step_data.model_dump()
        case_step_detailed.save()
        #
        page_step = PageSteps.objects.get(id=step_data.id)
        page_step.status = step_data.status
        page_step.save()
