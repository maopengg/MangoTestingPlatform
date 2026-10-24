from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_api.exceptions import API_VERSION_CASE_NOT_FOUND, AutoApiError
from src.interfaces.mcp.tools.api.case import register_case_tools
from src.interfaces.mcp.tools.api.helper_parts.case_result import _case_tree


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(func):
            self.tools[func.__name__] = func
            return func

        return register


class ApiCaseMcpErrorTests(SimpleTestCase):
    def test_case_tree_reports_actual_product_owner_permissions(self):
        helper = 'src.interfaces.mcp.tools.api.helper_parts.case_result'
        for user_id, is_owner, has_owner in ((4, True, True), (5, False, True), (4, False, False)):
            with self.subTest(user_id=user_id, has_owner=has_owner), patch(
                    'src.apps.auto_api.services.api_case.query.ApiCaseQueryService.get_instance',
                    return_value=SimpleNamespace(project_product_id=3),
            ), patch(
                f'{helper}.format_api_case',
                return_value={'id': 2371, 'is_product_owner': False, 'has_product_owner': False},
            ), patch(
                f'{helper}._api_case_version_summary', return_value={'publication_status': 'published'},
            ), patch(
                f'{helper}.mcp_current_user_id', return_value=user_id,
            ), patch(
                f'{helper}.TestCenterQuerySelector.is_project_product_owner', return_value=is_owner,
            ) as owner_check, patch(
                f'{helper}.TestCenterQuerySelector.has_project_product_owner', return_value=has_owner,
            ) as configured_check, patch(f'{helper}.ApiQuerySelector.api_case_detailed') as details:
                details.return_value.select_related.return_value.filter.return_value.order_by.return_value = []

                result = _case_tree(2371, include_result_data=False)

                self.assertEqual(result['case']['is_product_owner'], is_owner)
                self.assertEqual(result['case']['has_product_owner'], has_owner)
                self.assertEqual(result['case']['publication_status'], 'published')
                owner_check.assert_called_once_with(3, user_id)
                configured_check.assert_called_once_with(3)
                self.assertEqual(result['steps'], [])

    @patch('src.apps.auto_api.services.api_case.query.ApiCaseQueryService.get_instance')
    def test_case_tree_converts_missing_case_to_api_error(self, get_instance):
        get_instance.side_effect = AutoApiError(API_VERSION_CASE_NOT_FOUND, value=(999999,))

        with self.assertRaisesMessage(AutoApiError, 'API用例不存在，Case ID：999999'):
            _case_tree(999999)

    def test_full_case_detail_returns_business_error(self):
        registry = ToolRegistry()
        register_case_tools(registry)
        error = AutoApiError(API_VERSION_CASE_NOT_FOUND, value=(999999,))

        with patch(
                'src.interfaces.mcp.tools.api.case_tools.crud._case_tree',
                side_effect=error,
        ):
            result = registry.tools['get_api_case_detail_full'](999999)

        self.assertFalse(result['success'])
        self.assertEqual(result['message'], 'API用例不存在，Case ID：999999')
        self.assertEqual(result['error_code'], '1123')
