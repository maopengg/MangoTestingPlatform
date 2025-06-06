# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏

from django.db import connection

from src.auto_test.auto_ui.models import PageSteps, UiCase, UiCaseStepsDetailed
from src.enums.tools_enum import TaskEnum
from src.exceptions import *
from src.models.ui_model import UiCaseResultModel, PageStepsResultModel
from src.tools.decorator.retry import orm_retry


class TestReportWriting:

    @classmethod
    @orm_retry('update_page_step_status')
    def update_page_step_status(cls, data: PageStepsResultModel) -> None:
        try:
            log.ui.debug(f'开始写入步骤测试结果，步骤数据是：{data.model_dump_json()}')
            res = PageSteps.objects.get(id=data.id)
            res.status = data.status
            res.result_data = data.model_dump()
            res.save()
        except PageSteps.DoesNotExist:
            log.ui.error(
                '忽略这个报错，如果是在步骤详情中没有查到，可以忽略这个错误，步骤详情中的调试不会修改整个步骤状态')

    @classmethod
    @orm_retry('update_test_case')
    def update_test_case(cls, data: UiCaseResultModel):
        log.ui.debug(f'开始写入用例测试结果，用例的测试状态是：{data.status}')
        connection.ensure_connection()
        case = UiCase.objects.get(id=data.id)
        case.status = data.status
        case.save()
        for i in data.steps:
            cls.update_step(i)

        UiCaseStepsDetailed.objects \
            .filter(case_id=case.id, status=TaskEnum.PROCEED.value) \
            .update(status=TaskEnum.FAIL.value)

    @classmethod
    @orm_retry('update_step')
    def update_step(cls, step_data: PageStepsResultModel):
        log.ui.debug(f'开始写入用例中步骤测试结果，步骤数据是：{step_data.model_dump_json()}')

        case_step_detailed = UiCaseStepsDetailed.objects.get(id=step_data.case_step_details_id)
        case_step_detailed.status = step_data.status
        case_step_detailed.error_message = step_data.error_message
        case_step_detailed.result_data = step_data.model_dump()
        case_step_detailed.save()

        page_step = PageSteps.objects.get(id=step_data.id)
        page_step.status = step_data.status
        page_step.result_data = step_data.model_dump()
        page_step.save()
