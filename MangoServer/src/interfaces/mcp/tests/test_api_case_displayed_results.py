from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from src.interfaces.mcp.tools.api.helper_parts.case_result import (
    _api_case_step_result_items, _displayed_case_result,
)


class ApiCaseDisplayedResultMcpTests(SimpleTestCase):
    def setUp(self):
        self.result = {'status': 1, 'trace_id': 'selected', 'revision_id': 10, 'test_env': 2}
        self.selector = self.enterContext(patch(
            'src.interfaces.mcp.tools.api.helper_parts.case_result.ApiCaseListExecutionSelector'))
        self.selector.collect.return_value = {7: self.result}
        self.enterContext(patch('src.apps.auto_api.services.api_case.query.ApiCaseQueryService.get_instance'))
        self.loader = self.enterContext(patch(
            'src.interfaces.mcp.tools.api.helper_parts.case_result.ExecutionResultService.load_result_data'))
        self.legacy = self.enterContext(patch(
            'src.interfaces.mcp.tools.api.helper_parts.case_result.ExecutionResultService.latest_api_case_parameter_result'))

    def test_metadata_only_never_reads_result_body(self):
        self.assertEqual(_displayed_case_result(7, False), (self.result, {}))
        self.selector.collect.assert_called_once_with([7])
        self.selector.result_record.assert_not_called()
        self.loader.assert_not_called()

    def test_missing_exact_body_does_not_search_old_results(self):
        self.selector.result_record.return_value = None
        self.assertEqual(_displayed_case_result(7), (self.result, {}))
        self.selector.result_record.assert_called_once_with(7, self.result)
        self.loader.assert_not_called()
        self.legacy.assert_not_called()

    def test_body_is_loaded_only_once_from_selected_record(self):
        record = object()
        self.selector.result_record.return_value = record
        body = {'steps': [{'parameter_id': 10, 'status': 0}]}
        self.loader.return_value = body
        self.assertEqual(_displayed_case_result(7), (self.result, body))
        self.loader.assert_called_once_with(record)
        self.legacy.assert_not_called()

    def test_scenario_status_comes_from_selected_execution_not_mutable_row(self):
        body = {'steps': [{'parameter_id': 10, 'status': 0, 'error_message': 'expected failure'}]}
        parameter = SimpleNamespace(id=10, name='场景', status=1, case_detailed_id=20,
            case_detailed=SimpleNamespace(api_info=SimpleNamespace(name='接口')))
        query = MagicMock()
        query.count.return_value = 1
        query.__getitem__.return_value = [parameter]
        with patch('src.interfaces.mcp.tools.api.helper_parts.case_result._displayed_case_result',
                   return_value=(self.result, body)), patch(
            'src.interfaces.mcp.tools.api.helper_parts.case_result.ApiQuerySelector.api_case_detailed_parameter'
        ) as parameters:
            parameters.return_value.select_related.return_value.filter.return_value.order_by.return_value = query
            response = _api_case_step_result_items(7)
        self.assertEqual(response['list_result'], self.result)
        self.assertEqual(response['items'][0]['status'], 0)
        self.legacy.assert_not_called()
