from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.services.test_case.test_api_info import TestApiInfo
from src.common.testing import ObtainTestData


class ApiInfoRuntimeParametersTests(SimpleTestCase):
    def test_runtime_values_remain_typed_and_do_not_edit_the_interface(self):
        runner = TestApiInfo.__new__(TestApiInfo)
        runner.test_env = 3
        runner.test_setup = MagicMock()
        runner.test_setup.test_data = ObtainTestData()
        runner.save_api_info = MagicMock(return_value={"code": 200})
        api = MagicMock(id=1)
        with patch('src.apps.auto_api.services.test_case.test_api_info.ApiInfo.objects.get', return_value=api):
            runner.api_info_run(1, runtime_parameters={'runtime_page_body': {'cursor': 'next'}, 'limit': 5})
        self.assertEqual(runner.test_setup.test_data.replace('${{runtime_page_body}}'), {'cursor': 'next'})
        self.assertEqual(runner.test_setup.test_data.replace('${{limit}}'), 5)
        api.save.assert_not_called()

    def test_invalid_runtime_keys_are_rejected_before_any_database_access(self):
        runner = TestApiInfo.__new__(TestApiInfo)
        with patch('src.apps.auto_api.services.test_case.test_api_info.ApiInfo.objects.get') as query:
            with self.assertRaises(AutoApiError):
                runner.api_info_run(1, runtime_parameters={1: 'invalid'})
            query.assert_not_called()
