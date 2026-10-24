from types import SimpleNamespace

from django.test import SimpleTestCase

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.schemas.execution import ApiExecutionResponse
from src.apps.auto_api.services.base.case_parameter import CaseParameter


class DefaultAssertionGroupTests(SimpleTestCase):
    class FakeTestData:
        def replace(self, value):
            return value

        def get_json_path_value(self, response, expression):
            return response[expression]

    def setUp(self):
        test_data = self.FakeTestData()
        test_setup = SimpleNamespace(test_data=test_data, test_object=None)
        self.case_parameter = CaseParameter(
            test_setup,
            SimpleNamespace(),
            SimpleNamespace(is_schema=0, ass_schema=None),
            test_env=0,
        )
        self.response = ApiExecutionResponse(
            code=200,
            time=0.1,
            headers={},
            json={'code': 201},
            text='{"code":201}',
        )

    def run_assertions(self, assertions):
        self.case_parameter._CaseParameter__ass_jsonpath(self.response, assertions)

    def test_old_ungrouped_assertions_keep_and_behavior(self):
        with self.assertRaises(AutoApiError):
            self.run_assertions([
                {'actual': '$.code', 'method': 'p_is_equal_to', 'expect': 200},
                {'actual': '$.code', 'method': 'p_is_equal_to', 'expect': 201},
            ])
        self.assertEqual(self.case_parameter.ass_result[0].assertion_index, 1)

    def test_ungrouped_or_assertions_share_default_group(self):
        self.run_assertions([
            {'group_logic': 'OR', 'actual': '$.code', 'method': 'p_is_equal_to', 'expect': 200},
            {'group_logic': 'OR', 'actual': '$.code', 'method': 'p_is_equal_to', 'expect': 201},
        ])

        summary = self.case_parameter.ass_result[-1]
        self.assertEqual(summary.status, 1)
        self.assertEqual(summary.group_name, '未分组')
        self.assertEqual(summary.group_logic, 'OR')

    def test_grouped_results_keep_original_assertion_indices(self):
        self.run_assertions([
            {'group_name': '业务状态', 'group_logic': 'OR', 'actual': '$.code', 'method': 'p_is_equal_to',
             'expect': 200},
            {'group_name': '业务状态', 'group_logic': 'OR', 'actual': '$.code', 'method': 'p_is_equal_to',
             'expect': 201},
        ])

        results = self.case_parameter.ass_result
        self.assertEqual([result.assertion_index for result in results], [1, 2, None])
        self.assertEqual(results[-1].source_type, 'assertion_group')
        self.assertEqual(results[-1].group_source_type, 'jsonpath')

    def test_configuration_error_keeps_original_assertion_index(self):
        with self.assertRaises(AutoApiError):
            self.case_parameter._CaseParameter__ass_jsonpath(
                self.response,
                [
                    {'assertion_type': 'cache', 'actual': 'invalid', 'method': 'p_is_not_none'},
                    {'actual': '$.code', 'method': 'p_is_equal_to', 'expect': 201},
                ],
                continue_on_failure=True,
            )

        self.assertEqual([result.assertion_index for result in self.case_parameter.ass_result], [1, 2])

    def test_default_and_named_groups_must_both_pass(self):
        with self.assertRaises(AutoApiError):
            self.run_assertions([
                {'group_logic': 'OR', 'actual': '$.code', 'method': 'p_is_equal_to', 'expect': 200},
                {'group_logic': 'OR', 'actual': '$.code', 'method': 'p_is_equal_to', 'expect': 201},
                {
                    'group_name': '业务状态',
                    'group_logic': 'AND',
                    'actual': '$.code',
                    'method': 'p_is_equal_to',
                    'expect': 202,
                },
            ])
