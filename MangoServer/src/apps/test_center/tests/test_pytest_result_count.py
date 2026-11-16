from django.test import SimpleTestCase
from unittest.mock import patch
from types import SimpleNamespace
from mangotools.contracts import PytestExecutionResult, TestSuiteDetailResultContract
from mangotools.enums import TaskEnum

from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.schemas.execution import TestSuiteDetailResultSchema
from src.apps.test_center.services.reporting.testcounter import TestCounter
from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService
from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService


class PytestResultCountTests(SimpleTestCase):
    def result(self, **fields):
        return PytestExecutionResult(dispatch_id='example-dispatch', source_snapshot={}, id=1,
                                     name='example', status=1, **fields)

    def test_old_protocol_never_claims_complete_results(self):
        result = self.result(result_data=[{'status': 1}])
        self.assertFalse(result.results_complete)
        self.assertIsNone(TestCounter.completed_pytest_count(result))

    def test_complete_results_include_failed_and_warning_items_not_nested_steps(self):
        items = [{'status': 1, 'steps': [{'status': 1}] * 20}, {'status': 0}, {'status': TaskEnum.WARNING.value}]
        result = self.result(result_data=items, results_complete=True, collected_count=3)
        self.assertEqual(TestCounter.completed_pytest_count(result), 3)
        row = {'case_sum': 3, 'success': 1, 'fail': 1, 'warning': 1, 'status': 0}
        counts = TestSuiteSummaryService.execution_status_counts_from_rows([row])
        self.assertEqual((counts['success'], counts['fail'], counts['warning']), (1, 1, 1))

    def test_empty_partial_malformed_and_synthetic_error_results_preserve_estimate(self):
        for fields in (
            {'result_data': [], 'collected_count': 0},
            {'result_data': [{'status': 1}], 'collected_count': 10},
            {'result_data': {'status': 1}, 'collected_count': 1},
            {'result_data': [{'status': 1}], 'collected_count': 1, 'error_message': 'Interrupted'},
            {'result_data': [{'name': 'execution failed'}], 'collected_count': 1},
            {'result_data': [None], 'collected_count': 1},
        ):
            with self.subTest(fields=fields):
                self.assertIsNone(TestCounter.completed_pytest_count(self.result(results_complete=True, **fields)))

    def test_complete_marker_round_trips_through_shared_and_server_protocols(self):
        result = self.result(result_data=[{'status': 0}], collected_count=1, results_complete=True)
        wire = TestSuiteDetailResultContract(id=2, type=TestCaseTypeEnum.PYTEST.value,
                                            test_suite=3, status=0, result_data=result.model_dump(mode='json'))
        received = TestSuiteDetailResultSchema.from_contract(
            TestSuiteDetailResultContract.model_validate_json(wire.model_dump_json()))
        self.assertEqual(TestCounter.completed_pytest_count(received.result_data), 1)

    def test_corrected_actual_total_is_not_clamped_or_filled_with_artificial_warnings(self):
        for actual in (5, 10):
            items = [{'status': 1}] * (actual - 1) + [{'status': 0}]
            result = self.result(result_data=items, results_complete=True, collected_count=actual)
            detail = SimpleNamespace(case_sum=TestCounter.completed_pytest_count(result))
            with patch.object(TestSuiteExecutionResultService, 'get_result_data', return_value=items):
                counts = TestCounter.res_pytest(detail)
            self.assertEqual(counts, {'success': actual - 1, 'fail': 1, 'warning': 0})
