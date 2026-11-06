from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from mangotools.enums import StatusEnum

from src.apps.auto_api.services.test_case.test_case import TestCase as ApiRuntimeTestCase
from src.apps.auto_api.services.base.case_base import CaseBase
from src.apps.auto_api.exceptions import AutoApiError


class ApiCasePosteriorFailureTests(SimpleTestCase):
    def test_invalid_legacy_item_does_not_skip_later_cleanup_or_hide_failure(self):
        base = CaseBase.__new__(CaseBase)
        base.test_env = 0
        base.api_case = SimpleNamespace(id=1, project_product_id=1, posterior_sql=[
            None, {'key': '', 'value': 'DELETE FROM demo WHERE id=2'}])
        base.test_setup = Mock()
        base.test_setup.test_data.replace.side_effect = lambda value: value
        base.case_data_factory = Mock()
        with patch('src.apps.auto_api.services.base.case_base.execute_data_source_operation') as execute:
            with self.assertRaises(AutoApiError) as caught:
                base.case_posterior_main()
        execute.assert_called_once()
        base.case_data_factory.cleanup.assert_called_once()
        self.assertIn('第1项必须是对象', caught.exception.msg)

    def test_stopping_during_posterior_still_attempts_factory_cleanup(self):
        base = CaseBase.__new__(CaseBase)
        base.api_case = SimpleNamespace(posterior_sql=[{}])
        base._CaseBase__posterior_sql = Mock(side_effect=KeyboardInterrupt())
        base.case_data_factory = Mock()
        with self.assertRaises(KeyboardInterrupt):
            base.case_posterior_main()
        base.case_data_factory.cleanup.assert_called_once()

    def test_environment_exclusion_is_preserved_without_broadening_cleanup_scope(self):
        base = CaseBase.__new__(CaseBase)
        base.test_env = 0
        base.api_case = SimpleNamespace(id=1, project_product_id=1, posterior_sql=[
            {'key': '', 'test_envs': [1], 'value': 'DELETE FROM demo WHERE id=1'},
            {'key': '', 'test_envs': [0], 'value': 'DELETE FROM demo WHERE id=2'}])
        base.test_setup = Mock()
        base.test_setup.test_data.replace.side_effect = lambda value: value
        base.case_data_factory = Mock()
        with patch('src.apps.auto_api.services.base.sql_environment.EnvironmentEnum.get_key_list', return_value=[0, 1]), \
                patch('src.apps.auto_api.services.base.case_base.execute_data_source_operation') as execute:
            base.case_posterior_main()
        execute.assert_called_once()
        self.assertEqual(execute.call_args.args[2]['value'], 'DELETE FROM demo WHERE id=2')

    def test_posterior_items_all_attempted_once_and_factory_failure_is_not_lost(self):
        base = CaseBase.__new__(CaseBase)
        base.test_env = 0
        base.api_case = SimpleNamespace(id=1, project_product_id=1, posterior_sql=[
            {'key': '', 'value': 'DELETE FROM demo WHERE id=1'},
            {'key': '', 'value': 'DELETE FROM demo WHERE id=2'},
            {'key': '', 'value': 'DELETE FROM demo WHERE id=3'}])
        base.test_setup = Mock()
        base.test_setup.test_data.replace.side_effect = lambda value: value
        base.case_data_factory = Mock()
        base.case_data_factory.cleanup.side_effect = RuntimeError('factory-cleanup-failed')
        with patch('src.apps.auto_api.services.base.case_base.execute_data_source_operation',
                   side_effect=[RuntimeError('first-failed'), {'result': []}, RuntimeError('third-failed')]) as execute:
            with self.assertRaises(AutoApiError) as caught:
                base.case_posterior_main()
        self.assertEqual(execute.call_count, 3)
        base.case_data_factory.cleanup.assert_called_once()
        for message in ('first-failed', 'third-failed', 'factory-cleanup-failed'):
            self.assertIn(message, caught.exception.msg)

    def build_runtime(self, original_error=None):
        runtime = ApiRuntimeTestCase.__new__(ApiRuntimeTestCase)
        runtime.case_id = 2754
        runtime.test_suite = 554996414321
        runtime.test_suite_details = 212763
        runtime.api_case = SimpleNamespace(posterior_sql=[{'value': 'DELETE'}], status=1)
        runtime.api_case_result = SimpleNamespace(status=1, error_message=original_error)
        runtime.case_base = Mock()
        runtime.case_base.case_posterior_main.side_effect = RuntimeError('缺少后置缓存变量')
        runtime.trace_recorder = Mock()
        runtime.trace_recorder.start_step.return_value = 'posterior-step'
        return runtime

    def test_posterior_failure_marks_case_failed_without_raising(self):
        runtime = self.build_runtime()

        runtime.run_case_posterior()

        self.assertEqual(runtime.api_case_result.status, StatusEnum.FAIL.value)
        self.assertEqual(runtime.api_case.status, StatusEnum.FAIL.value)
        self.assertEqual(runtime.api_case_result.error_message, '用例后置处理失败：缺少后置缓存变量')
        runtime.trace_recorder.fail_step.assert_called_once_with(
            'posterior-step',
            '缺少后置缓存变量',
        )

    def test_posterior_failure_preserves_original_failure(self):
        runtime = self.build_runtime('接口场景失败')

        runtime.run_case_posterior()

        self.assertEqual(
            runtime.api_case_result.error_message,
            '接口场景失败；用例后置处理失败：缺少后置缓存变量',
        )
