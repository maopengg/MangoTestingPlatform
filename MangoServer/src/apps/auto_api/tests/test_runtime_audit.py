from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from mangotools.enums import StatusEnum

from src.apps.auto_api.services.execution.cases.test_case import TestCase as ApiRuntimeTestCase


class ApiCaseRuntimeAuditTests(SimpleTestCase):

    @patch('src.apps.auto_api.services.execution.cases.test_case.ApiCase.objects.filter')
    def test_case_status_update_does_not_touch_content_update_time(self, filter_mock):
        queryset = filter_mock.return_value

        ApiRuntimeTestCase.update_test_case(12, StatusEnum.SUCCESS.value)

        filter_mock.assert_called_once_with(id=12)
        queryset.update.assert_called_once_with(status=StatusEnum.SUCCESS.value)

    def test_step_status_save_does_not_touch_content_update_time(self):
        runtime = object.__new__(ApiRuntimeTestCase)
        runtime.revision_aggregate = None
        step = Mock()

        runtime.save_case_detailed_runtime_state(step)

        step.save.assert_called_once_with(update_fields=['status', 'error_message'])

    @patch('src.apps.auto_api.services.execution.cases.test_case.ApiCaseDetailedParameter.objects.filter')
    def test_scenario_status_update_does_not_touch_content_update_time(self, filter_mock):
        runtime = object.__new__(ApiRuntimeTestCase)
        runtime.revision_aggregate = None
        result = SimpleNamespace(status=StatusEnum.FAIL.value)
        queryset = filter_mock.return_value

        runtime.update_test_case_detailed_parameter(23, result)

        filter_mock.assert_called_once_with(id=23)
        queryset.update.assert_called_once_with(status=StatusEnum.FAIL.value)
