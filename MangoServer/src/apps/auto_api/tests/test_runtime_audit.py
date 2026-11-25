from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from mangotools.enums import StatusEnum
from mangotools.enums import TaskEnum

from src.apps.auto_api.services.execution.cases.test_case import TestCase as ApiRuntimeTestCase


class ApiCaseRuntimeAuditTests(SimpleTestCase):

    def test_reset_run_keeps_case_result_but_resets_step_progress(self):
        from src.apps.auto_api.services.execution.cases.run_status import ApiCaseRunStatusService as RunStatus
        module = 'src.apps.auto_api.services.execution.cases.run_status.'
        with patch.object(RunStatus, 'scoped_step_ids', return_value=[23]), \
             patch(module + 'ApiCase.objects.filter') as cases, \
             patch(module + 'ApiCaseDetailed.objects.filter') as steps, \
             patch(module + 'ApiCaseDetailedParameter.objects.filter') as scenarios:
            RunStatus.reset_single_run(12, None)
        cases.assert_not_called()
        steps.return_value.update.assert_called_once_with(status=TaskEnum.STAY_BEGIN.value, error_message=None)
        scenarios.return_value.update.assert_called_once_with(status=TaskEnum.STAY_BEGIN.value)

    @patch('src.apps.auto_api.services.execution.cases.test_case_parts.parameter.ApiCase.objects.filter')
    def test_start_does_not_replace_case_result(self, filter_mock):
        for status in (TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value):
            ApiRuntimeTestCase.update_test_case(12, status)
        filter_mock.assert_not_called()

    @patch('src.apps.auto_api.services.execution.cases.test_case_parts.parameter.ApiCase.objects.filter')
    def test_case_status_update_does_not_touch_content_update_time(self, filter_mock):
        queryset = filter_mock.return_value

        ApiRuntimeTestCase.update_test_case(12, StatusEnum.SUCCESS.value)

        filter_mock.assert_called_once_with(id=12)
        queryset.update.assert_called_once_with(status=StatusEnum.SUCCESS.value)

    @patch('src.apps.auto_api.services.execution.cases.test_case_parts.step.ApiCaseDetailed.objects.filter')
    def test_step_status_save_does_not_touch_content_update_time(self, filter_mock):
        runtime = object.__new__(ApiRuntimeTestCase)
        runtime.revision_aggregate = None
        runtime.case_id = 12
        step = SimpleNamespace(id=23, status=StatusEnum.SUCCESS.value, error_message=None)

        runtime.save_case_detailed_runtime_state(step)

        filter_mock.assert_called_once_with(case_id=12, id=23)
        filter_mock.return_value.update.assert_called_once_with(status=StatusEnum.SUCCESS.value, error_message=None)

    @patch('src.apps.auto_api.services.execution.cases.test_case_parts.parameter.ApiCaseDetailedParameter.objects.filter')
    def test_scenario_status_update_does_not_touch_content_update_time(self, filter_mock):
        runtime = object.__new__(ApiRuntimeTestCase)
        runtime.revision_aggregate = None
        runtime.case_id = 12
        result = SimpleNamespace(status=StatusEnum.FAIL.value, execution_context=None)
        queryset = filter_mock.return_value

        runtime.update_test_case_detailed_parameter(23, result)

        filter_mock.assert_called_once_with(id=23, case_detailed__case_id=12)
        queryset.update.assert_called_once_with(status=StatusEnum.FAIL.value)
