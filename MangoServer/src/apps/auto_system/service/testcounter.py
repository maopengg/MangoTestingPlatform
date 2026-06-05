# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-10-17 10:44
# @Author : 毛鹏
import re
from pathlib import Path

from src.apps.auto_api.models import ApiCaseDetailedParameter, ApiCaseDetailed
from src.apps.auto_pytest.models import PytestCase
from src.apps.auto_system.models import TestSuiteDetails
from src.apps.auto_system.service.test_suite.detail_result import TestSuiteDetailResultService
from src.common.enums.tools_enum import StatusEnum
from src.common.enums.tools_enum import TestCaseTypeEnum


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
        model.success = res['success']
        model.fail = res['fail']
        model.warning = res['warning']
        if model.fail > 0:
            model.status = StatusEnum.FAIL.value
        model.save()

    @staticmethod
    def res_api(test_suite_details) -> dict:
        case_counter = TestCounter.default_counter()
        result_data = TestSuiteDetailResultService.get_result_data(test_suite_details)
        if not result_data:
            case_counter['fail'] += test_suite_details.case_sum
            return case_counter
        for r in result_data:
            if r.get('status') == StatusEnum.SUCCESS.value:
                case_counter['success'] += 1
            else:
                case_counter['fail'] += 1
        TestCounter.fill_missing_failures(case_counter, test_suite_details.case_sum)
        return case_counter

    @staticmethod
    def res_pytest(test_suite_details) -> dict:
        case_counter = TestCounter.default_counter()
        result_data = TestSuiteDetailResultService.get_result_data(test_suite_details)
        if not result_data:
            case_counter['fail'] += test_suite_details.case_sum
            return case_counter
        for r in result_data:
            if r.get('status') == StatusEnum.SUCCESS.value:
                case_counter['success'] += 1
            else:
                case_counter['fail'] += 1
        TestCounter.fill_missing_failures(case_counter, test_suite_details.case_sum)
        return case_counter

    @staticmethod
    def res_ui(test_suite_details) -> dict:
        case_counter = TestCounter.default_counter()
        if test_suite_details.status == StatusEnum.SUCCESS.value:
            case_counter['success'] += 1
        else:
            case_counter['fail'] += 1
        return case_counter

    @staticmethod
    def default_counter() -> dict:
        return {'success': 0, 'fail': 0, 'warning': 0}

    @staticmethod
    def fill_missing_failures(case_counter: dict, case_sum: int):
        result_sum = case_counter['success'] + case_counter['fail'] + case_counter['warning']
        missing_sum = max((case_sum or 0) - result_sum, 0)
        case_counter['fail'] += missing_sum

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
        file_path = Path(model.file_path)
        test_count = 0
        test_function_pattern = re.compile(r'^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(')
        scenarios_pattern = re.compile(r'^\s*scenarios\s*\(\s*[\'"]([^\'"]+)[\'"]')
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    match = test_function_pattern.match(line)
                    if match:
                        function_name = match.group(1)
                        if function_name.startswith('test') or function_name.endswith('test'):
                            test_count += 1
                        continue

                    scenarios_match = scenarios_pattern.match(line)
                    if scenarios_match:
                        test_count += TestCounter.case_feature(file_path, scenarios_match.group(1))
        except FileNotFoundError:
            return 1
        except Exception:
            return 1
        return test_count or 1

    @staticmethod
    def case_feature(pytest_file_path: Path, feature_path: str) -> int:
        path = Path(feature_path)
        if not path.is_absolute():
            path = pytest_file_path.parent / path
        scenario_pattern = re.compile(r'^\s*(?:Scenario(?: Outline)?|场景(?:大纲)?):\s+')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return sum(1 for line in f if scenario_pattern.match(line))
        except FileNotFoundError:
            return 0
        except Exception:
            return 0
