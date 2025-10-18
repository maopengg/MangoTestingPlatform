# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-10-17 10:44
# @Author : 毛鹏
from src.auto_test.auto_api.models import ApiCaseDetailedParameter, ApiCaseDetailed
from src.auto_test.auto_system.models import TestSuiteDetails
from src.enums.tools_enum import StatusEnum
from src.enums.tools_enum import TestCaseTypeEnum
from src.models.system_model import CaseCounterModel


class TestCounter:

    @classmethod
    def res_main(cls, _id):
        model = TestSuiteDetails.objects.get(id=_id)
        if model.type == TestCaseTypeEnum.API.value:
            res = cls.res_api(model)
        elif model.type == TestCaseTypeEnum.UI.value:
            res = cls.res_ui(model)
        else:
            res = cls.res_pytest(model)
            model.case_sum = res.case_sum
        model.success = res.success
        model.fail = res.fail
        model.warning = res.warning
        model.save()

    @staticmethod
    def res_api(test_suite_details) -> CaseCounterModel:
        case_counter = CaseCounterModel()
        for r in test_suite_details.result_data:
            if r.get('status') == StatusEnum.SUCCESS.value:
                case_counter.success += 1
            else:
                case_counter.fail += 1
        return case_counter

    @staticmethod
    def res_pytest(test_suite_details) -> CaseCounterModel:
        case_counter = CaseCounterModel()
        if test_suite_details:
            for r in test_suite_details.result_data:
                case_counter.case_sum += 1
                if r.get('status') == StatusEnum.SUCCESS.value:
                    case_counter.success += 1
                else:
                    case_counter.fail += 1
        return case_counter

    @staticmethod
    def res_ui(test_suite_details) -> CaseCounterModel:
        case_counter = CaseCounterModel()
        if test_suite_details.status == StatusEnum.SUCCESS.value:
            case_counter.success += 1
        else:
            case_counter.fail += 1
        return case_counter

    @staticmethod
    def case_api(case_id):
        case_sum = ApiCaseDetailedParameter.objects.filter(
            case_detailed=ApiCaseDetailed.objects.first(case_id=case_id))
        return case_sum

    @staticmethod
    def case_ui(case_id):
        return 1

    @staticmethod
    def case_pytest(case_id):
        return 1
