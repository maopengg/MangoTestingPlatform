from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.schemas.execution import ApiExecutionResponse
from src.apps.auto_api.services.execution.base.api_base_test_setup import APIBaseTestSetup
from src.apps.auto_api.services.execution.base.case_parameter import CaseParameter


class AssertionAndScriptDiagnosticsTests(SimpleTestCase):
    def setUp(self):
        stub = patch('src.apps.system.services.configuration.system_config.SystemConfigService.get_environment_display_names',
                     return_value={})
        stub.start()
        self.addCleanup(stub.stop)

    def evaluator(self, assertions):
        data = SimpleNamespace(replace=lambda value: value, get_cache=lambda _: None)
        parameter = SimpleNamespace(ass_jsonpath=assertions, ass_general=[], ass_json_all=None,
                                    ass_text_all=None, ass_schema=None)
        setup = SimpleNamespace(test_data=data, test_object=None)
        return CaseParameter(setup, parameter, SimpleNamespace(is_schema=0, ass_schema=None), 0)

    def test_invalid_and_missing_jsonpath_continue_independent_assertions(self):
        for expression in ('$.missing', '$.data['):
            with self.subTest(expression=expression):
                evaluator = self.evaluator([
                    {'actual': expression, 'method': 'p_is_equal_to', 'expect': 1},
                    {'actual': '$.code', 'method': 'p_is_equal_to', 'expect': 200},
                ])
                with patch('src.apps.auto_api.services.execution.base.case_parameter.log.api.error') as logger:
                    results, status, message = evaluator.verify_all_assertions(
                        ApiExecutionResponse(code=200, time=0.1, headers={}, json={'code': 500}, text='{}'))
                self.assertEqual(status, 0)
                self.assertEqual(len(results), 2)
                self.assertNotIn('未知错误', message)
                self.assertIn('500', results[1].ass_msg)
                self.assertFalse(any('未知错误' in str(call) for call in logger.call_args_list))

    def test_or_group_survives_missing_field_when_another_assertion_passes(self):
        for group in ('', 'example'):
            with self.subTest(group=group):
                evaluator = self.evaluator([
                    {'actual': '$.missing', 'method': 'p_is_equal_to', 'expect': 1,
                     'group_name': group, 'group_logic': 'OR'},
                    {'actual': '$.code', 'method': 'p_is_equal_to', 'expect': 200,
                     'group_name': group, 'group_logic': 'OR'},
                ])
                results, status, message = evaluator.verify_all_assertions(
                    ApiExecutionResponse(code=200, time=0.1, headers={}, json={'code': 200}, text='{}'))
                self.assertEqual(status, 1)
                self.assertIsNone(message)
                self.assertEqual(len(results), 3)
                self.assertTrue(results[-1].group_result)

    def test_invalid_regex_does_not_skip_following_assertion(self):
        evaluator = self.evaluator([
            {'assertion_type': 'regex', 'actual': '[', 'method': 'p_is_equal_to', 'expect': 'value'},
            {'actual': '$.code', 'method': 'p_is_equal_to', 'expect': 200},
        ])
        results, status, message = evaluator.verify_all_assertions(
            ApiExecutionResponse(code=200, time=0.1, headers={}, json={'code': 500}, text='value'))
        self.assertEqual(status, 0)
        self.assertEqual(len(results), 2)
        self.assertNotIn('未知错误', message)

    def test_function_errors_log_only_identifiers_and_frames(self):
        scripts = (
            "token = 'secret-script'\ndef func(:\n    pass",
            "token = 'secret-script'\nraise RuntimeError('secret-initialization')",
            "def func():\n    token = 'secret-script'\n    raise RuntimeError('secret-runtime')",
            "def func():\n    token = 'secret-script'\n    return None",
        )
        for index, script in enumerate(scripts):
            with self.subTest(script_kind=len(script)):
                setup = APIBaseTestSetup.__new__(APIBaseTestSetup)
                setup.test_data = SimpleNamespace(replace=lambda value: value)
                setup.current_api_info_id = 3
                with patch('src.apps.auto_api.services.execution.base.api_base_test_setup.log') as logger:
                    if index < 3:
                        with self.assertRaises(AutoApiError):
                            setup.execute_analytic_func(script)
                        logger.api.error.assert_called_once()
                    else:
                        self.assertIsNone(setup.execute_analytic_func(script))
                        logger.api.error.assert_not_called()
                calls = str(logger.mock_calls)
                self.assertNotIn('secret', calls)
                self.assertNotIn(script, calls)
                if logger.api.error.called:
                    self.assertIn('api_custom_function_error', calls)
                    self.assertIn('script_sha256', calls)
