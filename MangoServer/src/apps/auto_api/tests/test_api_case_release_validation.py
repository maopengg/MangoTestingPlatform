from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from mangotools.enums import TaskEnum

from src.apps.auto_api.exceptions import API_CASE_PUBLICATION_REQUIRES_PASSED, AutoApiError
from src.apps.auto_api.models import ApiCase, ApiCaseRelease, ApiCaseRevision
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService


class ApiCaseReleaseValidationTests(SimpleTestCase):

    def test_prepublication_rejects_all_non_passed_states_before_writing(self):
        for status in TaskEnum:
            if status.value == TaskEnum.SUCCESS.value:
                continue
            with self.subTest(status=status), patch.object(
                ApiCase.objects, 'select_for_update',
            ) as cases, patch.object(ApiCaseRevision.objects, 'select_for_update') as revisions, patch.object(
                ApiCaseRelease.objects, 'filter',
            ) as releases, patch.object(ApiCaseRelease.objects, 'create') as create:
                cases.return_value.filter.return_value.first.return_value = SimpleNamespace(
                    id=17, status=status.value,
                )
                with self.assertRaises(AutoApiError) as error:
                    ApiCaseRevisionService.submit_prepublication.__wrapped__(ApiCaseRevisionService, 17, 31)
                self.assertEqual(error.exception.code, API_CASE_PUBLICATION_REQUIRES_PASSED.code)
                revisions.assert_not_called()
                releases.assert_not_called()
                create.assert_not_called()

    def test_publication_rejects_all_non_passed_execution_states_before_writing(self):
        for status in TaskEnum:
            if status.value == TaskEnum.SUCCESS.value:
                continue
            with self.subTest(status=status), patch.object(
                    ApiCase.objects, 'select_for_update',
            ) as cases, patch.object(
                ApiCaseRevision.objects, 'filter',
            ) as revisions, patch.object(
                ApiCaseRelease.objects, 'select_for_update',
            ) as releases:
                cases.return_value.filter.return_value.first.return_value = SimpleNamespace(
                    id=17, status=status.value,
                )
                with self.assertRaises(AutoApiError) as error:
                    ApiCaseRevisionService._publish_revision.__wrapped__(
                        ApiCaseRevisionService, 17, 31, publisher_id=9,
                    )
                self.assertEqual(error.exception.code, API_CASE_PUBLICATION_REQUIRES_PASSED.code)
                revisions.assert_not_called()
                releases.assert_not_called()

    def test_passed_case_can_submit_prepublication(self):
        revision = SimpleNamespace(id=31)
        with patch.object(ApiCase.objects, 'select_for_update') as cases, patch.object(
            ApiCaseRevision.objects, 'select_for_update',
        ) as revisions, patch.object(ApiCaseRevision.objects, 'filter') as candidates, patch.object(
            ApiCaseRelease.objects, 'filter',
        ) as releases, patch.object(ApiCaseRelease.objects, 'select_for_update') as locked_releases, patch.object(ApiCaseRelease.objects, 'create') as create, patch(
            'src.apps.auto_api.services.api_case.version_parts.recording.'
            'TestCenterQuerySelector.has_project_product_owner', return_value=True,
        ), patch.object(ApiCaseRevisionService, 'verify_execution_revision'), patch.object(
            ApiCaseRevisionService, 'verify_publishable_revision',
        ), patch.object(ApiCaseRevisionService, '_schedule_prepublication_todo_sync'):
            cases.return_value.filter.return_value.first.return_value = SimpleNamespace(
                id=17, status=TaskEnum.SUCCESS.value, project_product_id=4,
            )
            revisions.return_value.filter.return_value.first.return_value = revision
            candidates.return_value.order_by.return_value.values_list.return_value.first.return_value = 31
            releases.return_value.exists.return_value = False
            releases.return_value.aggregate.return_value = {'max_version': 0}
            locked_releases.return_value.filter.return_value.order_by.return_value.first.return_value = None
            result = ApiCaseRevisionService.submit_prepublication.__wrapped__(ApiCaseRevisionService, 17, 31)
            self.assertIs(result, create.return_value)
            self.assertEqual(create.call_args.kwargs['status'], 'prepublished')
            self.assertFalse(create.call_args.kwargs['is_current'])

    def test_passed_case_can_promote_prepublication_to_current_release(self):
        prepublication = SimpleNamespace(
            status='prepublished', replaced_release=None, save=Mock(),
        )
        release_queryset = Mock()
        release_queryset.filter.return_value.order_by.return_value.first.return_value = None
        release_queryset.filter.return_value.first.return_value = prepublication
        release_queryset.aggregate.return_value = {'max_version': 1}
        with patch.object(ApiCase.objects, 'select_for_update') as cases, patch.object(
                ApiCaseRevision.objects, 'filter',
        ) as revisions, patch.object(
            ApiCaseRelease.objects, 'select_for_update',
        ) as releases, patch.object(
            ApiCaseRevisionService, 'verify_execution_revision',
        ), patch.object(ApiCaseRevisionService, 'verify_publishable_revision'):
            cases.return_value.filter.return_value.first.return_value = SimpleNamespace(
                id=17, status=TaskEnum.SUCCESS.value,
            )
            revisions.return_value.first.return_value = SimpleNamespace(id=31)
            releases.return_value.filter.return_value = release_queryset
            result = ApiCaseRevisionService._publish_revision.__wrapped__(
                ApiCaseRevisionService, 17, 31, publisher_id=9,
            )

        self.assertIs(result, prepublication)
        self.assertEqual(result.status, ApiCaseRelease.STATUS_PUBLISHED)
        self.assertTrue(result.is_current)
        prepublication.save.assert_called_once()

    def test_missing_scenario_header_reports_step_and_scenario_position(self):
        revision = SimpleNamespace(
            payload={
                'api_case_detailed': [
                    {
                        'logical_id': 'step-1',
                        'api_info_id': 1,
                        'api_info_revision_id': 1,
                        'api_case_detailed_parameter': [
                            {'missing_header_ids': [999999]},
                        ],
                    },
                ],
            },
        )

        with self.assertRaises(AutoApiError) as error:
            ApiCaseRevisionService.verify_publishable_revision(revision)

        self.assertIn('第 1 个步骤的第 1 个场景请求头不存在', error.exception.msg)
