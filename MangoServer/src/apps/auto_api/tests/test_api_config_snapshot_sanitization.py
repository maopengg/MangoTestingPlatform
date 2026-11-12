from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_api.api.serializers.api_case_version import ApiCaseRevisionDetailSerializer
from src.apps.auto_api.api.serializers.api_info_version import ApiInfoRevisionDetailSerializer
from src.apps.auto_api.api.views.api_info import ApiInfoCRUD
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.auto_api.services.execution.base.api_base_test_setup.auth_manager import ApiAuthManager
from src.apps.auto_api.services.execution.base.assertion_diagnostics import value_preview
from src.apps.auto_api.services.configuration.version import ApiConfigSnapshotService


class ApiConfigSnapshotSanitizationTests(SimpleTestCase):

    def test_preserves_runtime_variable_in_sensitive_field(self):
        payload = {
            'app_id': '${{app_id}}',
            'app_secret': '${{app_secret}}',
            'authorization': 'Bearer ${{access_token}}',
        }

        self.assertEqual(ApiConfigSnapshotService.sanitize_value(payload), payload)

    def test_masks_plaintext_sensitive_field(self):
        payload = {
            'app_id': 'cli_app_id',
            'app_secret': 'plaintext-secret',
        }

        self.assertEqual(
            ApiConfigSnapshotService.sanitize_value(payload),
            {
                'app_id': 'cli_app_id',
                'app_secret': '***',
            },
        )

    def test_api_info_revision_detail_returns_exact_request_config(self):
        payload = {
            'api_info': {
                'body_config': {
                    'source_type': 'value',
                    'body': {
                        'app_id': '${{app_id}}',
                        'app_secret': '${{app_secret}}',
                    },
                },
            },
        }

        result = ApiInfoRevisionDetailSerializer.get_payload(
            SimpleNamespace(payload=payload),
        )

        self.assertEqual(result['api_info']['body_config'], payload['api_info']['body_config'])

    def test_api_case_revision_detail_returns_exact_request_config(self):
        payload = {
            'api_case': {
                'request_config': {
                    'app_id': 'actual-app-id',
                    'app_secret': 'actual-app-secret',
                },
            },
        }

        result = ApiCaseRevisionDetailSerializer.get_payload(
            SimpleNamespace(payload=payload),
        )

        self.assertEqual(result['api_case']['request_config'], payload['api_case']['request_config'])

    def test_assertion_diagnostic_returns_exact_api_data(self):
        self.assertEqual(
            value_preview({'app_secret': 'actual-app-secret'}),
            '{"app_secret": "actual-app-secret"}',
        )

    def test_partial_update_merges_current_runtime_before_changed_fields(self):
        instance = SimpleNamespace()
        current_runtime = SimpleNamespace()
        current_config = {
            'headers': {'X-Original': 'header'},
            'body_type': 'json',
            'body_config': {'source_type': 'value', 'body': {'original': True}},
        }

        with patch.object(
                ApiInfoRuntimeService,
                'current_payload',
                return_value=current_config,
        ):
            ApiInfoCRUD.attach_merged_runtime_config(
                instance,
                current_runtime,
                {'headers': {}},
            )

        self.assertEqual(instance.headers, {})
        self.assertEqual(instance.body_type, 'json')
        self.assertEqual(
            instance.body_config,
            {'source_type': 'value', 'body': {'original': True}},
        )

    def test_auth_refresh_fallback_uses_declared_jsonpath_value(self):
        manager = ApiAuthManager()
        config = SimpleNamespace(api_info_id=6)
        test_data = SimpleNamespace(
            replace=lambda value: value,
            get_json_path_value=lambda data, expression: data['tenant_access_token'],
        )
        test_setup = SimpleNamespace(test_data=test_data)
        response = SimpleNamespace(json={'tenant_access_token': 'token-value'})
        api_info = SimpleNamespace(
            posterior_json_path=[{'key': 'token', 'value': '$.tenant_access_token'}],
            posterior_re=[],
        )

        with patch.object(
                ApiInfoRuntimeService,
                'resolve_runtime',
                return_value=api_info,
        ):
            result = manager._collect_declared_api_cache_data(
                config,
                test_setup,
                {},
                response,
            )

        self.assertEqual(result, {'token': 'token-value'})

    def test_auth_refresh_returns_login_api_error(self):
        response = SimpleNamespace(error_msg='登录接口返回的具体错误')
        test_data = SimpleNamespace(get_all=lambda: {})
        test_setup = SimpleNamespace(
            skip_auth_load=False,
            test_data=test_data,
            init_test_object=lambda *args: None,
            init_public=lambda *args: None,
            api_request=lambda *args: response,
        )
        config = SimpleNamespace(
            api_info_id=6,
            project_product_id=2,
            test_env=2,
        )

        with self.assertRaisesMessage(AutoApiError, '登录接口返回的具体错误'):
            ApiAuthManager(test_setup)._refresh_by_api(config)
