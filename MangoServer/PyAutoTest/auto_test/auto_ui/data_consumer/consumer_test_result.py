# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
import json
import logging

from PyAutoTest.auto_test.auto_ui.models import UiPageSteps, UiCase
from PyAutoTest.auto_test.auto_ui.views.ui_case_result import UiCaseResultSerializers
from PyAutoTest.auto_test.auto_ui.views.ui_ele_result import UiEleResultSerializers
from PyAutoTest.auto_test.auto_ui.views.ui_page_steps_result import UiPageStepsResultSerializers
from PyAutoTest.enums.system_enum import IsItEnabled
from PyAutoTest.models.socket_model.ui_model import CaseResult, PageStepsResultModel, EleResult

log = logging.getLogger('ui')


class ConsumerTestResult:

    @classmethod
    def page_step_state_update(cls, data: PageStepsResultModel) -> None:
        try:
            res = UiPageSteps.objects.get(id=data.page_step_id)
            res.type = IsItEnabled.right.value if data.status else IsItEnabled.wrong.value
            res.save()
        except UiPageSteps.DoesNotExist as e:
            # 处理找不到对应记录的情况
            log.error(f"当前查询结果是空，请检查id是否在数据库中存在id：{data.page_step_id}报错：{e}")

    @classmethod
    def update_case_state(cls, case_id: int, status: int):
        try:
            case = UiCase.objects.get(id=case_id)
            case.state = status
            case.save()
        except UiCase.DoesNotExist as e:
            # 处理找不到对应记录的情况
            log.error(f"当前查询结果是空，请检查id是否在数据库中存在id：{case_id}报错：{e}")

    @classmethod
    def update_case_result(cls, data: CaseResult):
        for i in data.case_res_list:
            cls.update_page_steps(i)
        data = data.dict()
        data['case_cache_data'] = str(json.dumps(data['case_cache_data']))
        serializer = UiCaseResultSerializers(data=data)
        if serializer.is_valid():
            serializer.save()
        else:
            log.error(f'增加用例结果，请联系管理员进行查看，错误信息：{serializer.errors}')

    @classmethod
    def update_page_steps(cls, data: PageStepsResultModel):
        for i in data.ele_result_list:
            cls.update_ele(i)
        serializer = UiPageStepsResultSerializers(data=data.dict())
        if serializer.is_valid():
            serializer.save()
        else:
            log.error(f'增加用例步骤结果，请联系管理员进行查看，错误信息：{serializer.errors}')

    @classmethod
    def update_ele(cls, data: EleResult):
        data = data.dict()
        data['ope_value'] = str(data['ope_value'])
        data['ass_value'] = str(data['ass_value'])
        serializer = UiEleResultSerializers(data=data)
        if serializer.is_valid():
            serializer.save()
        else:
            log.error(f'增加元素结果，请联系管理员进行查看，错误信息：{serializer.errors}')
