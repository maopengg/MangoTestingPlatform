from unittest.mock import patch

from django.test import TestCase

from src.apps.auto_api.api.serializers.api_case_version import ApiCaseRevisionListSerializer
from src.apps.auto_api.api.views.api_case import ApiCaseCRUD
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.models import ApiCase, ApiCaseRelease, ApiCaseRevision
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.test_center.models import ProductModule, Project, ProjectProduct
from src.apps.user.models import User
from src.apps.task_center.enums.execution import AutomationExecutionSceneEnum, AutomationExecutionScopeEnum
from src.apps.task_center.services.selection.api_case_binding import ApiCaseTaskBindingService
from src.apps.task_center.services.selection.case_selection import ScheduledTaskCaseSelectionService
from src.apps.test_center.enums import TestCaseTypeEnum


class ApiCasePublicationLifecycleTests(TestCase):
    def setUp(self):
        product = ProjectProduct.objects.create(project=Project.objects.create(name='Publication'), name='Example')
        module = ProductModule.objects.create(project_product=product, name='Example Module')
        owner = User.objects.create(name='Reviewer', username='publication_reviewer', password='unused')
        self.case = ApiCase.objects.create(project_product=product, module=module, case_people=owner, name='Example Case', status=1)
        self.first = ApiCaseRevision.objects.create(api_case=self.case, revision_no=1, payload={}, checksum='first')
        self.old = ApiCaseRelease.objects.create(api_case=self.case, revision=self.first, version_no=1, version_label='V1')
        self.candidate = ApiCaseRevision.objects.create(api_case=self.case, revision_no=2, payload={}, checksum='second')
        for name in ('verify_execution_revision', 'verify_publishable_revision', '_verify_product_owner', '_schedule_prepublication_todo_sync'):
            patcher = patch.object(ApiCaseRevisionService, name)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch('src.apps.auto_api.services.api_case.version_parts.recording.TestCenterQuerySelector.has_project_product_owner', return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def submit(self):
        return ApiCaseRevisionService.submit_prepublication(self.case.id, self.candidate.id)

    def test_submit_and_approve_have_one_current_state(self):
        pending = self.submit()
        self.old.refresh_from_db()
        self.assertFalse(self.old.is_current)
        self.assertEqual(self.old.status, 'published')
        self.assertEqual(pending.replaced_release_id, self.old.id)
        state = ApiCaseRevisionService.get_publication_state(self.case.id)
        self.assertEqual(state.publication_status, 'prepublished')
        self.assertIsNone(state.published_release_id)
        with self.assertRaises(AutoApiError):
            ApiCaseRevisionService.resolve_current_published(self.case.id)
        with self.assertRaises(AutoApiError):
            ApiCaseRevisionService.resolve_release(self.case.id, self.old.id)
        approved = ApiCaseRevisionService.approve_prepublication(self.case.id, operator_id=None)
        self.assertTrue(approved.is_current)
        self.assertEqual(approved.replaced_release_id, self.old.id)
        self.assertEqual(ApiCaseRevisionService.get_publication_state(self.case.id).publication_status, 'published')
        self.assertEqual(ApiCaseRelease.objects.filter(api_case=self.case, is_current=True).count(), 1)

    def test_revert_does_not_restore_history(self):
        self.submit()
        ApiCaseRevisionService.revert_prepublication(self.case.id, operator_id=None)
        self.assertEqual(ApiCaseRevisionService.get_publication_state(self.case.id).publication_status, 'unpublished')
        self.assertFalse(ApiCaseRelease.objects.filter(api_case=self.case, is_current=True).exists())
        self.assertTrue(ApiCaseRelease.objects.filter(id=self.old.id).exists())

    def test_failed_submit_rolls_back_current_release_demotion(self):
        with patch.object(ApiCaseRelease.objects, 'create', side_effect=RuntimeError('test rollback')):
            with self.assertRaises(RuntimeError):
                self.submit()
        self.old.refresh_from_db()
        self.assertTrue(self.old.is_current)
        self.assertFalse(ApiCaseRelease.objects.filter(api_case=self.case, status='prepublished').exists())

    def test_task_selection_excludes_prepublished_and_reverted_cases(self):
        self.case.scenario_tags = [AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value]
        self.case.save(update_fields=['scenario_tags'])
        def selected_ids():
            return [item.case_id for item in ScheduledTaskCaseSelectionService.select(
                project_product_id=self.case.project_product_id, module=None, test_env=0,
                execution_scenes=self.case.scenario_tags, execution_scope=AutomationExecutionScopeEnum.MANUAL.value,
                case_types=[TestCaseTypeEnum.API.value],
            )]
        self.assertEqual(selected_ids(), [self.case.id])
        self.submit()
        self.assertEqual(selected_ids(), [])
        with self.assertRaises(AutoApiError):
            ApiCaseTaskBindingService.resolve_execution_selection(self.case.id, 'published')
        ApiCaseRevisionService.revert_prepublication(self.case.id, operator_id=None)
        self.assertEqual(selected_ids(), [])

    def test_existing_overlapping_versions_are_read_as_prepublication_only(self):
        self.submit()
        ApiCaseRelease.objects.filter(id=self.old.id).update(is_current=True)
        self.assertFalse(ApiQuerySelector.current_published_case_releases().filter(api_case=self.case).exists())
        state = ApiCaseRevisionService.get_publication_state(self.case.id)
        self.assertEqual(state.publication_status, 'prepublished')
        self.assertIsNone(state.published_release_id)
        revision = ApiCaseRevision.objects.prefetch_related('releases').get(id=self.first.id)
        data = ApiCaseRevisionListSerializer(revision, context={'has_prepublication': True}).data
        self.assertFalse(data['release']['is_current'])
        annotated = ApiCaseCRUD.annotate_publication_state(ApiCase.objects.filter(id=self.case.id)).first()
        self.assertEqual(annotated.publication_status, 'prepublished')
        self.assertIsNone(annotated.published_release_id)
        ApiCaseRevisionService.revert_prepublication(self.case.id, operator_id=None)
        self.assertFalse(ApiCaseRelease.objects.filter(api_case=self.case, is_current=True).exists())
