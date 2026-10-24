from types import SimpleNamespace

from django.test import SimpleTestCase

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.services.test_case.test_case import TestCase as ApiCaseRunner
from src.common.exceptions import ErrorDefinition


class ApiCaseScenarioResultNameTests(SimpleTestCase):

    def test_result_name_replaces_cache_placeholders(self):
        runner = ApiCaseRunner.__new__(ApiCaseRunner)
        runner.test_setup = SimpleNamespace(
            test_data=SimpleNamespace(
                replace=lambda value: value.replace('${{user_id}}', 'U1001'),
            ),
        )
        parameter = SimpleNamespace(name='创建用户-${{user_id}}')
        case_detailed = SimpleNamespace(id=10, api_info=SimpleNamespace(name='创建用户'))

        self.assertEqual(
            runner.resolve_scenario_result_name(parameter, case_detailed),
            '创建用户-U1001',
        )

    def test_missing_cache_keeps_original_name(self):
        def raise_missing_cache(_value):
            raise AutoApiError(ErrorDefinition(code=300, message='缓存不存在'))

        runner = ApiCaseRunner.__new__(ApiCaseRunner)
        runner.test_setup = SimpleNamespace(
            test_data=SimpleNamespace(replace=raise_missing_cache),
        )
        parameter = SimpleNamespace(name='创建用户-${{missing_user}}')
        case_detailed = SimpleNamespace(id=10, api_info=SimpleNamespace(name='创建用户'))

        self.assertEqual(
            runner.resolve_scenario_result_name(parameter, case_detailed),
            '创建用户-${{missing_user}}',
        )
