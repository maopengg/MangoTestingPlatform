# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-10-17 10:44
# @Author : 毛鹏
from src.auto_test.auto_api.models import ApiCaseDetailedParameter, ApiCaseDetailed
from src.auto_test.auto_pytest.models import PytestCase
from src.auto_test.auto_system.models import TestSuiteDetails
from src.enums.tools_enum import StatusEnum
from src.enums.tools_enum import TestCaseTypeEnum
from src.models.system_model import CaseCounterModel
from src.tools.decorator.retry import async_task_db_connection


class TestCounter:

    @classmethod
    @async_task_db_connection(max_retries=3, retry_delay=3)
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
        if not test_suite_details.result_data:
            case_counter.fail += test_suite_details.case_sum
            return case_counter
        for r in test_suite_details.result_data:
            if r.get('status') == StatusEnum.SUCCESS.value:
                case_counter.success += 1
            else:
                case_counter.fail += 1
        return case_counter

    @staticmethod
    def res_pytest(test_suite_details) -> CaseCounterModel:
        case_counter = CaseCounterModel()
        if not test_suite_details.result_data:
            case_counter.fail += test_suite_details.case_sum
            return case_counter
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
            case_detailed__in=ApiCaseDetailed.objects.filter(case_id=case_id))
        return case_sum.count()

    @staticmethod
    def case_ui(case_id):
        return 1

    @staticmethod
    def case_pytest(case_id):
        model = PytestCase.objects.get(id=case_id)
        file_path = model.file_path
        test_count = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    # 去除空白字符并检查是否以def test开头
                    stripped_line = line.strip()
                    if stripped_line.startswith('def test'):
                        test_count += 1
        except FileNotFoundError:
            return 1
        except Exception:
            return 1
        return test_count
