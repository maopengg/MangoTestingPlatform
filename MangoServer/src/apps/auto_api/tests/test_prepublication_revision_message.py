from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.auto_api.enums import ApiCaseReleaseStatusEnum
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService


class PrepublicationRevisionMessageTests(SimpleTestCase):
    def test_old_candidate_still_blocks_revision_with_actionable_message(self):
        with (
            patch('src.apps.auto_api.services.api_case.version_parts.recording.ApiCase.objects') as cases,
            patch('src.apps.auto_api.services.api_case.version_parts.recording.ApiCaseRelease.objects') as releases,
            patch('src.apps.auto_api.services.api_case.version_parts.recording.'
                  'ApiExecutableSnapshotService.capture_case') as snapshot,
        ):
            cases.select_for_update.return_value.filter.return_value.first.return_value = Mock()
            releases.filter.return_value.exists.return_value = True
            with self.assertRaises(AutoApiError) as raised:
                ApiCaseRevisionService.record_current.__wrapped__(ApiCaseRevisionService, 6031)
        self.assertEqual(raised.exception.code, 31212)
        message = str(raised.exception)
        for text in ['产品负责人', '用例版本页面', '退回旧候选', '当前编辑态的执行结果不会更新旧候选']:
            self.assertIn(text, message)
        releases.filter.assert_called_once_with(api_case_id=6031, status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value)
        snapshot.assert_not_called()

    def test_revert_does_not_require_owner_and_preserves_revision(self):
        path = 'src.apps.auto_api.services.api_case.version_parts.recording'
        candidate = Mock()
        with patch(path + '.ApiCase.objects') as cases, patch(path + '.ApiCaseRelease.objects') as releases, \
                patch.object(ApiCaseRevisionService, '_verify_product_owner') as owner, \
                patch.object(ApiCaseRevisionService, '_schedule_prepublication_todo_sync') as sync:
            cases.select_for_update.return_value.filter.return_value.first.return_value = Mock(project_product_id=9)
            releases.select_for_update.return_value.select_related.return_value.filter.return_value.first.return_value = candidate
            result = ApiCaseRevisionService.revert_prepublication.__wrapped__(ApiCaseRevisionService, 6031, operator_id=7)
            owner.assert_not_called()
            self.assertIs(result, candidate.revision)
            candidate.delete.assert_called_once_with()
            candidate.revision.delete.assert_not_called()
            sync.assert_called_once_with(9)

    def test_approve_still_enforces_product_owner(self):
        path = 'src.apps.auto_api.services.api_case.version_parts.recording'
        from src.apps.auto_api.exceptions import API_CASE_PREPUBLICATION_APPROVAL_FORBIDDEN
        with patch(path + '.ApiCase.objects') as cases, patch(path + '.ApiCaseRelease.objects') as releases, \
                patch.object(ApiCaseRevisionService, '_verify_product_owner',
                             side_effect=AutoApiError(API_CASE_PREPUBLICATION_APPROVAL_FORBIDDEN)) as owner:
            case = cases.select_for_update.return_value.filter.return_value.first.return_value
            with self.assertRaises(AutoApiError) as raised:
                ApiCaseRevisionService.approve_prepublication.__wrapped__(ApiCaseRevisionService, 6031, operator_id=7)
            self.assertEqual(raised.exception.code, 31208)
            owner.assert_called_once_with(case, 7)
            releases.select_for_update.assert_not_called()

    def test_http_revert_keeps_product_scope_boundary(self):
        from src.apps.auto_api.api.views.api_case_version import ApiCasePrepublicationViews
        from src.apps.user.services.authorization.http_permission_registry import HTTP_PERMISSION_RULES
        self.assertEqual(HTTP_PERMISSION_RULES[(
            'src.apps.auto_api.api.views.api_case_version.ApiCasePrepublicationViews', 'revert', 'delete',
        )], 'api.case:change')
        view = ApiCasePrepublicationViews()
        for allowed in (True, False):
            with self.subTest(allowed=allowed), \
                    patch.object(view, 'has_case_scope', return_value=allowed), \
                    patch.object(view, 'operator_id', return_value=7), \
                    patch.object(ApiCaseRevisionService, 'revert_prepublication', return_value=Mock(api_case_id=6031)) as revert:
                view.revert(Mock(data={'case_id': 6031}))
                if allowed:
                    revert.assert_called_once_with(6031, operator_id=7)
                else:
                    revert.assert_not_called()

    def test_mcp_revert_uses_current_operator_and_keeps_change_permission(self):
        from src.interfaces.mcp.tools.api.case_tools.revision import register_case_revision_tools
        from src.apps.user.services.authorization.mcp_permission_registry import MCP_PERMISSION_RULES
        self.assertEqual(MCP_PERMISSION_RULES['update_api_case_publication_status']['permission_key'], 'api.case:change')
        self.assertTrue(MCP_PERMISSION_RULES['update_api_case_publication_status']['project_scoped'])
        functions = {}
        def register(function):
            functions[function.__name__] = function
            return function
        server = Mock()
        server.tool.side_effect = lambda: register
        register_case_revision_tools(server)
        with patch('src.interfaces.mcp.tools.api.case_tools.revision.current_user', return_value=Mock(id=7)), \
                patch.object(ApiCaseRevisionService, 'revert_prepublication', return_value=Mock(api_case_id=6031, id=8209)) as revert:
            functions['update_api_case_publication_status'](6031, 'unpublished')
            revert.assert_called_once_with(6031, operator_id=7)
