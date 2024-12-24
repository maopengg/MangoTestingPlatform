# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-12-24 11:19
# @Author : 毛鹏
from django.db import connection

from PyAutoTest.auto_test.auto_api.models import ApiCase, ApiInfo, ApiCaseDetailed
from PyAutoTest.models.api_model import ApiCaseResultModel, ApiCaseStepsResultModel
from PyAutoTest.tools.decorator.retry import orm_retry


class UpdateTestStatus:

    @classmethod
    @orm_retry('update_api_case')
    def update_api_case(cls, data: ApiCaseResultModel):
        connection.ensure_connection()
        case = ApiCase.objects.get(id=data.id)
        case.status = data.status
        case.save()
        for i in data.steps:
            cls.update_api_info(i)

    @classmethod
    @orm_retry('update_api_info')
    def update_api_info(cls, step_data: ApiCaseStepsResultModel):
        case_step_detailed = ApiInfo.objects.get(id=step_data.api_info_id)
        case_step_detailed.status = step_data.status
        case_step_detailed.save()
        #
        page_step = ApiCaseDetailed.objects.get(id=step_data.id)
        page_step.status = step_data.status
        page_step.result_data = step_data.model_dump()
        page_step.save()
