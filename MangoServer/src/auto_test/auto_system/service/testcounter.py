# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-10-17 10:44
# @Author : 毛鹏
from src.auto_test.auto_system.models import TestSuiteDetails
from src.enums.tools_enum import StatusEnum
from src.enums.tools_enum import TestCaseTypeEnum
from src.models.system_model import CaseCounterModel


class TestCounter:

    @staticmethod
    def res_api(test_suite_id: int | None = None) -> CaseCounterModel:
        if test_suite_id is None:
            case_result = TestSuiteDetails.objects.all()
        else:
            case_result = TestSuiteDetails.objects.filter(test_suite_id=test_suite_id, type=TestCaseTypeEnum.API.value)
        case_counter = CaseCounterModel()
        if not case_result.exists():
            return case_counter
        for i in case_result:
            for r in i.result_data:
                case_counter.case_sum += 1
                case_counter.step_sum += 1
                if r.get('status') == StatusEnum.SUCCESS.value:
                    case_counter.success += 1
                else:
                    case_counter.fail += 1
        return case_counter

    @staticmethod
    def res_pytest(test_suite_id: int | None = None) -> CaseCounterModel:
        if test_suite_id is None:
            case_result = TestSuiteDetails.objects.all()
        else:
            case_result = TestSuiteDetails.objects.filter(test_suite_id=test_suite_id,
                                                          type=TestCaseTypeEnum.PYTEST.value)
        case_counter = CaseCounterModel()
        if not case_result.exists():
            return case_counter

        for i in case_result:
            if i.result_data:
                for r in i.result_data:
                    case_counter.case_sum += 1
                    if r.get('status') == StatusEnum.SUCCESS.value:
                        case_counter.success += 1
                    else:
                        case_counter.fail += 1
        return case_counter

    @staticmethod
    def res_ui(test_suite_id: int | None = None) -> CaseCounterModel:
        if test_suite_id is None:
            case_result = TestSuiteDetails.objects.all()
        else:
            case_result = TestSuiteDetails.objects.filter(test_suite_id=test_suite_id, type=TestCaseTypeEnum.UI.value)
        case_counter = CaseCounterModel()
        if not case_result.exists():
            return case_counter

        case_counter.case_sum = case_result.count()
        case_counter.success = case_result.filter(status=StatusEnum.SUCCESS.value).count()
        case_counter.fail = case_result.filter(status=StatusEnum.FAIL.value).count()
        for i in case_result:
            case_counter.step_sum += len(i.result_data)
        return case_counter

    @staticmethod
    def case_api() -> CaseCounterModel:
        pass

    @staticmethod
    def case_ui() -> CaseCounterModel:
        pass

    @staticmethod
    def case_pytest() -> CaseCounterModel:
        pass
