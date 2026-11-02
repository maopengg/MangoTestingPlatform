from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from mangotools.enums import StatusEnum

from src.apps.auto_ui.enums.case import UiCasePublicationStatusEnum as Publication
from src.apps.auto_ui.exceptions import AutoUiError
from src.apps.auto_ui.exceptions.definitions import (
    UI_CASE_PUBLICATION_INVALID_TRANSITION, UI_CASE_PUBLICATION_OWNER_REQUIRED,
    UI_CASE_PUBLICATION_REQUIRES_PASSED,
)
from src.apps.auto_ui.models import UiCase
from src.apps.auto_ui.selectors.case_publication import UiCasePublicationSelector
from src.apps.auto_ui.services.asset_mutation import UiAssetMutationService
from src.apps.auto_ui.services.case_publication import UiCasePublicationService
from src.apps.auto_ui.services.asset_copy import UiAssetCopyService
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.task_center.enums.execution import AutomationExecutionScopeEnum
from src.apps.task_center.models import Tasks, TasksDetails
from src.apps.task_center.services.selection.case_binding import TaskCaseBindingService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.auto_ui.api.views.ui_case import UiCaseViews
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.interfaces.mcp.authentication import permission_error
from src.interfaces.mcp.tools.ui.case import register_case_tools


class UiCasePublicationTests(SimpleTestCase):
    def case(self, status=Publication.UNPUBLISHED.value, execution=StatusEnum.SUCCESS.value):
        return SimpleNamespace(id=1, publication_status=status,
                               project_product_id=4, status=execution, save=Mock())

    def transition(self, case, target, *, owner=True, has_owner=True):
        with patch.object(UiCase.objects, 'select_for_update') as cases, patch.object(
            TestCenterQuerySelector, 'is_project_product_owner', return_value=owner,
        ), patch.object(TestCenterQuerySelector, 'has_project_product_owner', return_value=has_owner):
            cases.return_value.filter.return_value.first.return_value = case
            return UiCasePublicationService.transition.__wrapped__(1, target, operator_id=9)

    def test_passed_non_owner_can_submit_but_not_execute_on_schedule(self):
        case = self.case()
        self.transition(case, Publication.PREPUBLISHED.value, owner=False)
        self.assertEqual(case.publication_status, Publication.PREPUBLISHED.value)
        self.assertEqual(case.publication_status, Publication.PREPUBLISHED.value)
        case.save.assert_called_once()

    def test_owner_can_approve_and_revert(self):
        case = self.case(Publication.PREPUBLISHED.value)
        self.transition(case, Publication.PUBLISHED.value)
        self.assertEqual(case.publication_status, Publication.PUBLISHED.value)
        self.transition(case, Publication.UNPUBLISHED.value)
        self.assertEqual(case.publication_status, Publication.UNPUBLISHED.value)

    def test_non_passed_cases_cannot_submit_or_be_approved(self):
        for execution in StatusEnum:
            if execution.value == StatusEnum.SUCCESS.value:
                continue
            for current, target in ((Publication.UNPUBLISHED.value, Publication.PREPUBLISHED.value),
                                    (Publication.PREPUBLISHED.value, Publication.PUBLISHED.value)):
                with self.subTest(execution=execution, target=target):
                    case = self.case(current, execution.value)
                    with self.assertRaises(AutoUiError) as raised:
                        self.transition(case, target)
                    self.assertEqual(raised.exception.code, UI_CASE_PUBLICATION_REQUIRES_PASSED.code)
                    case.save.assert_not_called()

    def test_non_owner_cannot_approve_or_revert_even_when_passed(self):
        for target in (Publication.PUBLISHED.value, Publication.UNPUBLISHED.value):
            case = self.case(Publication.PREPUBLISHED.value)
            with self.assertRaises(AutoUiError) as raised:
                self.transition(case, target, owner=False)
            self.assertEqual(raised.exception.code, UI_CASE_PUBLICATION_OWNER_REQUIRED.code)
            case.save.assert_not_called()

    def test_unpublished_case_cannot_skip_prepublication(self):
        case = self.case()
        with self.assertRaises(AutoUiError) as raised:
            self.transition(case, Publication.PUBLISHED.value)
        self.assertEqual(raised.exception.code, UI_CASE_PUBLICATION_INVALID_TRANSITION.code)
        case.save.assert_not_called()

    def test_failed_prepublication_can_be_returned_by_owner(self):
        case = self.case(Publication.PREPUBLISHED.value, StatusEnum.FAIL.value)
        self.transition(case, Publication.UNPUBLISHED.value)
        self.assertEqual(case.publication_status, Publication.UNPUBLISHED.value)

    def test_submission_requires_product_owner_configuration(self):
        case = self.case()
        with self.assertRaises(AutoUiError):
            self.transition(case, Publication.PREPUBLISHED.value, has_owner=False)
        case.save.assert_not_called()

    def test_publication_status_is_the_only_model_source(self):
        self.assertNotIn('is_published', {field.name for field in UiCase._meta.fields})
        field = UiCase._meta.get_field('publication_status')
        self.assertEqual(field.default, Publication.UNPUBLISHED.value)
        self.assertFalse(field.null)
        for status in Publication.get_key_list():
            self.assertEqual(UiCasePublicationSelector.status(self.case(status)), status)

    def test_generic_mutations_cannot_bypass_publication_workflow(self):
        for fields in ({'publication_status': 'published'},):
            with self.assertRaises(AutoUiError):
                UiAssetMutationService.create_case(fields)
            with self.assertRaises(AutoUiError):
                UiAssetMutationService.update_case(1, fields)

    def test_status_filter_uses_publication_status(self):
        queryset = Mock()
        UiCasePublicationSelector.filter_status(queryset, Publication.PUBLISHED.value)
        queryset.filter.assert_called_once_with(publication_status='published')

    def test_all_status_does_not_add_a_filter(self):
        queryset = Mock()
        self.assertIs(UiCasePublicationSelector.filter_status(queryset, None), queryset)
        queryset.filter.assert_not_called()

    def test_copy_resets_publication_without_boolean_or_nullable_state(self):
        source = self.case(Publication.PUBLISHED.value)
        source.name = 'Source case'
        with patch.object(UiCase.objects, 'select_for_update') as query, patch.object(
            UiAssetCopyService, '_clone', return_value=SimpleNamespace(id=2),
        ) as clone, patch('src.apps.auto_ui.services.asset_copy.UiCaseStepsDetailed.objects.filter') as steps:
            query.return_value.get.return_value = source
            steps.return_value.order_by.return_value = []
            UiAssetCopyService.copy_case.__func__.__wrapped__(UiAssetCopyService, 1, operator_id=9)
        overrides = clone.call_args.kwargs['overrides']
        self.assertEqual(overrides['publication_status'], Publication.UNPUBLISHED.value)
        self.assertNotIn('is_published', overrides)

    def test_task_binding_uses_publication_status(self):
        task = SimpleNamespace(execution_scope=AutomationExecutionScopeEnum.MANUAL.value,
                               case_types=[TestCaseTypeEnum.UI.value], project_product_id=4, module_id=None)
        with patch.object(Tasks.objects, 'get', return_value=task), patch.object(
            UiCase.objects, 'filter',
        ) as cases, patch.object(TasksDetails.objects, 'filter') as details:
            cases.return_value.values_list.return_value = [(1, 4, None), (2, 4, None)]
            cases.return_value.exclude.return_value.values_list.return_value = [2]
            details.return_value.values_list.return_value = []
            result = TaskCaseBindingService.inspect_bind(1, TestCaseTypeEnum.UI.value, [1, 2])
        cases.return_value.exclude.assert_called_once_with(publication_status='published')
        self.assertEqual(result.created_ids, [1])
        self.assertEqual(result.unpublished_ids, [2])

    def test_rest_flow_uses_shared_service_and_returns_status(self):
        view = UiCaseViews()
        request = SimpleNamespace(data={'case_id': 1, 'target_status': 'prepublished'}, user={'id': 9})
        case = self.case(Publication.PREPUBLISHED.value)
        with patch.object(view, '_has_case_scope', return_value=True), patch.object(
            UiCasePublicationService, 'transition', return_value=case,
        ) as transition:
            response = view.set_publication(request)
        transition.assert_called_once_with(1, 'prepublished', operator_id=9)
        self.assertEqual(response.data['data']['publication_status'], 'prepublished')

    def test_rest_flow_rejects_out_of_scope_before_service(self):
        view = UiCaseViews()
        request = SimpleNamespace(data={'case_id': 1, 'target_status': 'prepublished'}, user={'id': 9})
        with patch.object(view, '_has_case_scope', return_value=False), patch.object(
            UiCasePublicationService, 'transition',
        ) as transition:
            response = view.set_publication(request)
        transition.assert_not_called()
        self.assertNotEqual(response.data['code'], 200)

    def test_rest_publication_requires_explicit_publish_permission(self):
        view = UiCaseViews()
        view.action = 'set_publication'
        request = SimpleNamespace(method='PUT', path='/api/ui/case/publication',
                                  data={'case_id': 1, 'target_status': 'prepublished'}, query_params={},
                                  user=SimpleNamespace(user_obj=SimpleNamespace(id=9)))
        view.request = request
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False):
            for permissions, expected in (({'ui.case:change'}, True), ({'ui.case:change'}, False),
                                          ({'ui.case:read'}, False)):
                with patch.object(PermissionMenuService, 'permission_keys_for_user', return_value=permissions):
                    self.assertEqual(MenuActionPermission().has_permission(request, view), expected)

    def test_mcp_publication_requires_publish_permission_and_scope(self):
        user = SimpleNamespace(id=9)
        arguments = {'case_id': 1, 'fields': {'publication_status': 'prepublished'}}
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), patch(
            'src.interfaces.mcp.authentication.resolve_project_product_ids', return_value={4},
        ), patch.object(ProjectProductScopeService, 'has_project_product', return_value=True):
            with patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'ui.case:change'}):
                self.assertIsNotNone(permission_error(user, 'update_ui_case', arguments))
            with patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'ui.case:change'}):
                self.assertIsNone(permission_error(user, 'update_ui_case', arguments))
                with patch.object(ProjectProductScopeService, 'has_project_product', return_value=False):
                    self.assertIsNotNone(permission_error(user, 'update_ui_case', arguments))

    def test_mcp_status_update_uses_shared_service(self):
        tools = {}

        class Capture:
            def tool(self):
                def register(function):
                    tools[function.__name__] = function
                    return function
                return register

        register_case_tools(Capture())
        case = self.case(Publication.PREPUBLISHED.value)
        with patch('src.interfaces.mcp.tools.ui.case.current_user', return_value=SimpleNamespace(id=9)), patch.object(
            UiCasePublicationService, 'transition', return_value=case,
        ) as transition:
            result = tools['update_ui_case'](1, {'publication_status': 'prepublished'})
        transition.assert_called_once_with(1, 'prepublished', operator_id=9)
        self.assertEqual(result['data']['publication_status'], 'prepublished')
        with self.assertRaises(AutoUiError):
            tools['update_ui_case'](1, {'publication_status': 'published', 'name': 'changed'})
