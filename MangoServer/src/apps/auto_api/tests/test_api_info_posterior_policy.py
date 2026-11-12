from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from src.apps.auto_api.schemas.execution import ApiExecutionRequest, ApiExecutionResponse
from src.apps.auto_api.services.execution.base.api_base_test_setup import APIBaseTestSetup


def response(code: int) -> ApiExecutionResponse:
    return ApiExecutionResponse(
        code=code,
        time=0.1,
        url='https://example.com/api',
        headers={},
        response_mode='http',
        request_protocol_type='http',
        json={'code': code},
    )


class ApiInfoPosteriorPolicyTest(TestCase):
    @staticmethod
    def setup_with_response(result: ApiExecutionResponse):
        setup = APIBaseTestSetup.__new__(APIBaseTestSetup)
        setup.current_api_info_id = None
        setup.init_test_object = Mock()
        setup.init_public = Mock()
        setup.request_data_clean = Mock(side_effect=lambda value: value)
        setup.http = Mock(return_value=result)
        setup.api_info_posterior_json_path = Mock()
        setup.api_info_posterior_json_re = Mock()
        setup.execute_analytic_func = Mock()
        return setup

    @staticmethod
    def api_info():
        return SimpleNamespace(
            id=1,
            name='权限校验',
            project_product_id=1,
            protocol_type='http',
            posterior_re=None,
            posterior_json_path='$.data.token',
            posterior_func=None,
        )

    @staticmethod
    def request_model():
        return ApiExecutionRequest(
            method='GET',
            url='/permission',
            protocol_type='http',
            body_type='none',
        )

    def test_non_2xx_skips_api_info_posterior(self):
        setup = self.setup_with_response(response(403))

        result = setup.api_request(1, 1, self.request_model(), api_info=self.api_info())

        setup.api_info_posterior_json_path.assert_not_called()
        self.assertIn('已跳过', result.api_info_posterior_skipped_reason)
        self.assertIsNone(result.error_msg)

    def test_2xx_still_runs_api_info_posterior(self):
        setup = self.setup_with_response(response(200))

        result = setup.api_request(1, 1, self.request_model(), api_info=self.api_info())

        setup.api_info_posterior_json_path.assert_called_once()
        self.assertIsNone(result.api_info_posterior_skipped_reason)

    def test_user_assertion_policy_skips_public_posterior_even_for_2xx(self):
        setup = self.setup_with_response(response(200))

        result = setup.api_request(
            1,
            1,
            self.request_model(),
            api_info=self.api_info(),
            apply_api_info_posterior=False,
        )

        setup.api_info_posterior_json_path.assert_not_called()
        self.assertIn('场景已配置断言', result.api_info_posterior_skipped_reason)

    def test_case_request_does_not_reload_public_cache(self):
        setup = self.setup_with_response(response(200))
        runtime_cache = {'token': 'step-token'}
        setup.init_public.side_effect = lambda *args: runtime_cache.update(token='auth-token')

        setup.api_request(
            1,
            1,
            self.request_model(),
            api_info=self.api_info(),
            initialize_public_context=False,
        )

        setup.init_public.assert_not_called()
        self.assertEqual(runtime_cache['token'], 'step-token')
