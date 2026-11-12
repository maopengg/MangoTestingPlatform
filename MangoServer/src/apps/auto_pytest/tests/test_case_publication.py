from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from django.http import QueryDict
from django.test import SimpleTestCase
from fastmcp import Client
from fastmcp.server.auth import AccessToken
from mangotools.enums import StatusEnum

from src.apps.auto_pytest.api.serializers.pytest_case_mutation import PytestCaseSerializers
from src.apps.auto_pytest.api.views.pytest_case import PytestCaseViews
from src.apps.auto_pytest.enums import PytestAssetStatusEnum, PytestSourceStatusEnum
from src.apps.auto_pytest.enums.case import PytestCasePublicationStatusEnum as Publication
from src.apps.auto_pytest.exceptions import AutoPytestError
from src.apps.auto_pytest.models import PytestCase
from src.apps.auto_pytest.selectors.case_publication import PytestCasePublicationSelector as Selector
from src.apps.auto_pytest.services.assets.case_publication import PytestCasePublicationService as Service
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.task_center.enums.execution import AutomationExecutionScopeEnum
from src.apps.task_center.models import Tasks, TasksDetails
from src.apps.task_center.services.selection.case_binding import TaskCaseBindingService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService
from src.interfaces.mcp.authentication import MangoAuthorizationMiddleware, permission_error
from src.interfaces.mcp.server import mcp_asgi_app
from src.interfaces.mcp.tools.pytest.case import register_case_tools
from src.interfaces.mcp.tools.pytest.helpers import _case_summary


class PytestCasePublicationTests(SimpleTestCase):
    def case(self, status=Publication.UNPUBLISHED.value, execution=StatusEnum.SUCCESS.value):
        return SimpleNamespace(id=1, publication_status=status,
                               project_product=SimpleNamespace(id=99, project_product_id=4), status=execution,
                               source_status=PytestSourceStatusEnum.ACTIVE.value,
                               asset_status=PytestAssetStatusEnum.PUBLISHED.value if status == 'published' else 0,
                               save=Mock())

    def transition(self, case, target, owner=True, has_owner=True):
        with patch.object(PytestCase.objects, 'select_for_update') as query, patch.object(
            TestCenterQuerySelector, 'is_project_product_owner', return_value=owner,
        ) as check_owner, patch.object(
            TestCenterQuerySelector, 'has_project_product_owner', return_value=has_owner,
        ) as check_config:
            query.return_value.select_related.return_value.filter.return_value.first.return_value = case
            result = Service.transition.__wrapped__(1, target, operator_id=9)
            if target == Publication.PREPUBLISHED.value:
                check_config.assert_called_once_with(4)
            else:
                check_owner.assert_called_once_with(4, 9)
            return result

    def test_passed_case_can_submit_without_owner_identity(self):
        case = self.case()
        self.transition(case, 'prepublished', owner=False)
        self.assertEqual(case.publication_status, 'prepublished')
        self.assertEqual(case.publication_status, Publication.PREPUBLISHED.value)
        self.assertEqual(case.asset_status, 0)

    def test_owner_approves_and_reverts_using_business_product_not_pytest_project(self):
        case = self.case('prepublished')
        self.transition(case, 'published')
        self.assertEqual(case.publication_status, Publication.PUBLISHED.value)
        self.assertEqual(case.asset_status, 1)
        self.transition(case, 'unpublished')
        self.assertEqual(case.publication_status, Publication.UNPUBLISHED.value)
        self.assertEqual(case.asset_status, 0)

    def test_non_passed_cases_cannot_submit_or_approve(self):
        for execution in StatusEnum:
            if execution.value == StatusEnum.SUCCESS.value:
                continue
            for current, target in (('unpublished', 'prepublished'), ('prepublished', 'published')):
                with self.subTest(execution=execution, target=target), self.assertRaises(AutoPytestError):
                    self.transition(self.case(current, execution.value), target)

    def test_non_owner_cannot_approve_or_revert(self):
        for target in ('published', 'unpublished'):
            with self.subTest(target=target), self.assertRaises(AutoPytestError):
                self.transition(self.case('prepublished'), target, owner=False)

    def test_cannot_skip_prepublication_or_repeat_status(self):
        for current, target in (('unpublished', 'published'), ('prepublished', 'prepublished'),
                                ('published', 'prepublished'), ('unpublished', 'invalid')):
            with self.subTest(current=current, target=target), self.assertRaises(AutoPytestError):
                self.transition(self.case(current), target)

    def test_submission_requires_configured_owner_and_valid_product(self):
        with self.assertRaises(AutoPytestError):
            self.transition(self.case(), 'prepublished', has_owner=False)
        with self.assertRaises(AutoPytestError):
            self.transition(None, 'prepublished')
        case = self.case()
        case.project_product.project_product_id = None
        with self.assertRaises(AutoPytestError):
            self.transition(case, 'prepublished')

    def test_unavailable_sources_and_assets_cannot_publish(self):
        for field, values in (
            ('source_status', (PytestSourceStatusEnum.MISSING, PytestSourceStatusEnum.PARSE_FAILED,
                               PytestSourceStatusEnum.CONFLICT)),
            ('asset_status', (PytestAssetStatusEnum.DISABLED, PytestAssetStatusEnum.ARCHIVED,
                              PytestAssetStatusEnum.IGNORED)),
        ):
            for value in values:
                case = self.case()
                setattr(case, field, value.value)
                with self.subTest(field=field, value=value), self.assertRaises(AutoPytestError):
                    self.transition(case, 'prepublished')
                case.save.assert_not_called()

    def test_failed_pending_case_can_be_returned(self):
        case = self.case('prepublished', StatusEnum.FAIL.value)
        self.transition(case, 'unpublished')
        self.assertEqual(case.publication_status, Publication.UNPUBLISHED.value)

    def test_publication_status_is_the_only_model_source(self):
        fields = {field.name for field in PytestCase._meta.fields}
        self.assertNotIn('is_published', fields)
        field = PytestCase._meta.get_field('publication_status')
        self.assertEqual(field.default, 'unpublished')
        self.assertFalse(field.null)
        for status in Publication.get_key_list():
            self.assertEqual(Selector.status(self.case(status)), status)

    def test_mcp_read_uses_publication_status(self):
        case = self.case('published')
        with patch('src.interfaces.mcp.tools.pytest.helpers.model_to_dict', return_value={'publication_status': 'published'}):
            self.assertEqual(_case_summary(case)['publication_status'], 'published')

    def test_search_filters_accept_multiselect(self):
        query = Mock()
        query.filter.return_value = query
        Selector.filter_search(query, QueryDict('status__in=0,1&publication_status__in=published,unpublished'))
        self.assertEqual(query.filter.call_args_list[0].kwargs, {'status__in': [0, 1]})
        self.assertEqual(query.filter.call_args.kwargs,
                         {'publication_status__in': ['published', 'unpublished']})
        self.assertIs(Selector.filter_status(query, []), query)

    def test_task_binding_rejects_non_published_cases_using_new_status(self):
        task = SimpleNamespace(execution_scope=AutomationExecutionScopeEnum.MANUAL.value,
                               case_types=[TestCaseTypeEnum.PYTEST.value], project_product_id=4, module_id=None)
        with patch.object(Tasks.objects, 'get', return_value=task), patch.object(
            PytestCase.objects, 'filter',
        ) as cases, patch.object(TasksDetails.objects, 'filter') as details:
            cases.return_value.values_list.return_value = [(1, 4, None), (2, 4, None)]
            cases.return_value.exclude.return_value.values_list.return_value = [2]
            details.return_value.values_list.return_value = []
            result = TaskCaseBindingService.inspect_bind(1, TestCaseTypeEnum.PYTEST.value, [1, 2])
        cases.return_value.exclude.assert_called_once_with(publication_status='published')
        self.assertEqual(result.created_ids, [1])
        self.assertEqual(result.unpublished_ids, [2])

    def test_generic_asset_edit_cannot_publish_or_unpublish(self):
        for case, target in ((self.case(), 1), (self.case('published'), 0), (self.case('prepublished'), 2)):
            with self.subTest(target=target), self.assertRaises(AutoPytestError):
                Service.verify_asset_edit(case, target)
        Service.verify_asset_edit(self.case(), 2)
        Service.verify_asset_edit(self.case('published'), 1)
        Service.verify_asset_edit(self.case('prepublished'), 0)
        fields = PytestCaseSerializers.Meta.read_only_fields
        self.assertIn('publication_status', fields)

    def test_rest_uses_shared_service_and_rejects_out_of_scope(self):
        view = PytestCaseViews()
        request = SimpleNamespace(data={'case_id': 1, 'target_status': 'prepublished'}, user={'id': 9})
        with patch.object(view, '_has_case_scope', return_value=True), patch.object(
            Service, 'transition', return_value=self.case('prepublished'),
        ) as transition:
            response = view.set_publication(request)
        transition.assert_called_once_with(1, 'prepublished', operator_id=9)
        self.assertEqual(response.data['data']['publication_status'], 'prepublished')
        with patch.object(view, '_has_case_scope', return_value=False), patch.object(Service, 'transition') as transition:
            response = view.set_publication(request)
        transition.assert_not_called()
        self.assertNotEqual(response.data['code'], 200)

    def test_rest_requires_change_permission(self):
        view = PytestCaseViews()
        view.action = 'set_publication'
        request = SimpleNamespace(method='PUT', path='/api/pytest/case/publication', data={}, query_params={},
                                  user=SimpleNamespace(user_obj=SimpleNamespace(id=9)))
        view.request = request
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False):
            for permissions, expected in (({'pytest.case:change'}, True), ({'pytest.case:read'}, False),
                                          (set(), False)):
                with patch.object(PermissionMenuService, 'permission_keys_for_user', return_value=permissions):
                    self.assertEqual(MenuActionPermission().has_permission(request, view), expected)

    def test_mcp_requires_change_permission_and_data_scope(self):
        user = SimpleNamespace(id=9)
        arguments = {'case_id': 1, 'target_status': 'prepublished'}
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), patch(
            'src.interfaces.mcp.authentication.resolve_project_product_ids', return_value={4},
        ), patch.object(ProjectProductScopeService, 'has_project_product', return_value=True):
            with patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'pytest.case:read'}):
                self.assertIsNotNone(permission_error(user, 'update_pytest_case_publication_status', arguments))
            with patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'pytest.case:change'}):
                self.assertIsNone(permission_error(user, 'update_pytest_case_publication_status', arguments))
                with patch.object(ProjectProductScopeService, 'has_project_product', return_value=False):
                    self.assertIsNotNone(permission_error(user, 'update_pytest_case_publication_status', arguments))

    def test_mcp_delegates_transition(self):
        tools = {}

        class Capture:
            def tool(self):
                def register(function):
                    tools[function.__name__] = function
                    return function
                return register

        register_case_tools(Capture())
        with patch('src.interfaces.mcp.tools.pytest.case.current_user', return_value=SimpleNamespace(id=9)), patch.object(
            Service, 'transition', return_value=self.case('prepublished'),
        ) as transition:
            tools['update_pytest_case_publication_status'](1, 'prepublished')
        transition.assert_called_once_with(1, 'prepublished', operator_id=9)

    async def test_authenticated_clients_discover_publication_tool_in_root_and_domain(self):
        for scope, visible in (('pytest.case:change', True), ('pytest.case:read', False)):
            access = AccessToken(token='test-pytest-key', client_id='pytest-publisher', subject='9', scopes=[scope],
                                 claims={'user_id': 9, 'is_super_admin': False})
            with patch.object(MangoAuthorizationMiddleware, '_access', new=AsyncMock(return_value=access)):
                for domain in (None, 'pytest'):
                    with self.subTest(domain=domain, scope=scope):
                        async with Client(mcp_asgi_app(domain).fastmcp_server) as client:
                            names = [tool.name for tool in await client.list_tools()]
                        self.assertEqual('update_pytest_case_publication_status' in names, visible)
