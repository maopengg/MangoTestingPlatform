from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.schemas.execution import ApiExecutionRequest, ApiExecutionResponse
from src.apps.auto_api.services.execution.base.api_base_test_setup import APIBaseTestSetup


class ApiInfoDebugVariableTests(SimpleTestCase):

    @staticmethod
    def api_info():
        return SimpleNamespace(
            id=1,
            name='查询供应商',
            project_product_id=1,
            protocol_type='http',
            posterior_re=None,
            posterior_json_path=None,
            posterior_func=None,
        )

    @staticmethod
    def request_model():
        return ApiExecutionRequest(
            method='GET',
            url='https://example.com/vendors/${{known_id}}/${{vendor_id}}',
            protocol_type='http',
            body_type='none',
        )

    @patch(
        'src.apps.auto_api.services.execution.base.api_base_test_setup.base_request.CacheDataValue.get_cache_value',
        return_value=15,
    )
    def test_api_info_debug_replaces_cached_value_and_preserves_missing_value(self, _mock_timeout):
        setup = APIBaseTestSetup()
        setup.test_data.set_cache('known_id', 'V100')
        response = ApiExecutionResponse(code=200, time=0.1, headers={}, json={}, text='{}')

        with patch.object(setup, 'init_test_object'), \
                patch.object(setup, 'init_public'), \
                patch.object(setup, 'http', return_value=response) as http:
            setup.api_request(
                1,
                0,
                request_model=self.request_model(),
                api_info=self.api_info(),
                preserve_unresolved_cache_placeholders=True,
            )

        cleaned_request = http.call_args.args[0]
        self.assertEqual(
            cleaned_request.url,
            'https://example.com/vendors/V100/${{vendor_id}}',
        )

    @patch(
        'src.apps.auto_api.services.execution.base.api_base_test_setup.base_request.CacheDataValue.get_cache_value',
        return_value=15,
    )
    def test_default_api_request_keeps_authorization_and_case_execution_strict(self, _mock_timeout):
        setup = APIBaseTestSetup()

        with patch.object(setup, 'init_test_object'), \
                patch.object(setup, 'init_public'), \
                self.assertRaises(AutoApiError):
            setup.api_request(
                1,
                0,
                request_model=self.request_model(),
                api_info=self.api_info(),
            )
