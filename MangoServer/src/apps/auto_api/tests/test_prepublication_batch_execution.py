from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.auto_api.services.api_case.version_parts import selection
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.services.reporting.test_suite.retry import TestSuiteRetryService


class PrepublicationBatchExecutionTests(SimpleTestCase):
    def resolve(self, cases, candidates):
        case_manager = MagicMock()
        case_manager.select_for_update.return_value.filter.return_value.only.return_value = cases
        releases = MagicMock()
        releases.filter.return_value.select_related.return_value = candidates
        return patch.object(selection.ApiCase, 'objects', case_manager), patch.object(
            selection.ApiCaseRelease, 'objects', releases)

    def candidate(self, case_id=1, revision_id=101):
        revision = SimpleNamespace(id=revision_id, api_case_id=case_id, revision_no=3,
                                   checksum=f'checksum-{revision_id}')
        return SimpleNamespace(api_case_id=case_id, revision=revision)

    def batch(self, ids):
        return ApiCaseRevisionService.resolve_batch_executions.__wrapped__(
            ApiCaseRevisionService, ids, execution_version='prepublished')

    def test_accepts_three_modes_and_rejects_unknown(self):
        for mode in ('editing', 'prepublished', 'published'):
            self.assertEqual(ApiCaseRevisionService.normalize_batch_execution_version(mode), mode)
        with self.assertRaises(AutoApiError):
            ApiCaseRevisionService.normalize_batch_execution_version('latest')

    def test_pins_candidate_not_current_editing_or_published(self):
        case = SimpleNamespace(id=1, name='候选测试')
        candidate = self.candidate()
        case_patch, release_patch = self.resolve([case], [candidate])
        with case_patch, release_patch, patch.object(ApiCaseRevisionService, 'verify_execution_revision') as verify:
            result = self.batch([1])[1]
        verify.assert_called_once_with(candidate.revision)
        self.assertEqual(result.case_revision_id, 101)
        self.assertEqual(result.checksum, 'checksum-101')
        self.assertEqual(result.version_label, '预发布 r3')
        self.assertEqual(result.execution_source, 'prepublished')
        self.assertIsNone(result.case_release_id)
        candidate.revision.id = 999
        self.assertEqual(result.case_revision_id, 101)

    def test_missing_candidate_rejects_whole_batch_with_case_identity(self):
        cases = [SimpleNamespace(id=1, name='有候选'), SimpleNamespace(id=2, name='未提交')]
        case_patch, release_patch = self.resolve(cases, [self.candidate()])
        with case_patch, release_patch, patch.object(ApiCaseRevisionService, 'verify_execution_revision') as verify:
            with self.assertRaises(AutoApiError) as caught:
                self.batch([1, 2])
        self.assertIn('2-未提交', caught.exception.msg)
        verify.assert_not_called()

    def test_candidate_query_uses_prepublication_status(self):
        case_patch, release_patch = self.resolve([SimpleNamespace(id=1, name='候选')], [self.candidate()])
        with case_patch, release_patch as manager, patch.object(ApiCaseRevisionService, 'verify_execution_revision'):
            self.batch([1])
        manager.filter.assert_called_once_with(api_case_id__in=[1], status='prepublished')

    def test_invalid_candidate_revision_is_rejected(self):
        case_patch, release_patch = self.resolve([SimpleNamespace(id=1, name='候选')], [self.candidate()])
        with case_patch, release_patch, patch.object(ApiCaseRevisionService, 'verify_execution_revision', side_effect=RuntimeError('checksum')):
            with self.assertRaisesRegex(RuntimeError, 'checksum'):
                self.batch([1])

    def test_retry_does_not_fall_back_to_editing_after_candidate_reverted(self):
        revision = SimpleNamespace(id=101, api_case_id=1, revision_no=3, checksum='frozen', source='mcp')
        detail = SimpleNamespace(type=TestCaseTypeEnum.API.value, case_id=1, api_case_revision_id=101,
            api_case_release_id=None, config_checksum='frozen', test_suite=SimpleNamespace(tasks_id=None))
        with patch.object(selection.ApiCaseRevision, 'objects') as manager, \
                patch.object(ApiCaseRevisionService, 'verify_execution_revision'), \
                patch('src.apps.test_center.services.reporting.test_suite.retry.ApiCaseTaskBindingService.resolve_execution_selection') as published:
            manager.filter.return_value.first.return_value = revision
            TestSuiteRetryService.refresh_current_api_release(detail)
        self.assertEqual(detail.api_case_revision_id, 101)
        self.assertEqual(detail.config_checksum, 'frozen')
        published.assert_not_called()

    def test_deleted_pinned_revision_is_not_silently_replaced(self):
        with patch.object(selection.ApiCaseRevision, 'objects') as manager:
            manager.filter.return_value.first.return_value = None
            with self.assertRaises(AutoApiError):
                ApiCaseRevisionService.resolve_manual_revision_retry(1, 101)

    def test_legacy_editing_snapshot_remains_editing(self):
        with patch.object(selection.ApiCaseRevision, 'objects') as manager:
            manager.filter.return_value.first.return_value = SimpleNamespace(source='batch_execution_snapshot')
            self.assertIsNone(ApiCaseRevisionService.resolve_manual_revision_retry(1, 101))
