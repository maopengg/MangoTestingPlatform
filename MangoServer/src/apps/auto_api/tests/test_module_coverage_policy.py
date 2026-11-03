from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from django.http import QueryDict
from django.test import SimpleTestCase
from django.urls import resolve
from fastmcp import Client
from fastmcp.server.auth import AccessToken
from pydantic import ValidationError

from src.apps.auto_api.enums.module_coverage import ModuleCoverageInterfaceCoverageStatus, ModuleCoveragePolicy
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.models import ModuleCoverageInterfaceSnapshot, ModuleCoverageModuleInterface
from src.apps.auto_api.schemas.module_coverage import ModuleCoveragePolicyUpdate
from src.apps.auto_api.services.module_coverage import ModuleCoverageService as Service
from src.apps.auto_api.tests.test_module_coverage import valid_interface_payload, valid_payload
from src.apps.auto_api.tests import test_module_coverage_overview as overview_helpers
from src.apps.test_center.models import ProjectProduct
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.selectors.querysets import UserQuerySelector
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.apps.user.services.mcp_permission_registry import MCP_PERMISSION_RULES
from src.interfaces.mcp.authentication import MangoAuthorizationMiddleware
from src.interfaces.mcp.server import _tool_operation, mcp_asgi_app


def excluded_snapshot(identity=1, product=9, **values):
    return SimpleNamespace(id=identity, project_product_id=product, module_interface_id=identity,
                           module_interface=SimpleNamespace(id=identity, current_snapshot_id=identity,
                                                            current_snapshot=None,
                                                            coverage_policy='excluded',
                                                            coverage_reason="专用集成，不在本模块范围"), **values)


class ModuleCoveragePolicyTests(SimpleTestCase):
    def test_schema_and_model_defaults(self):
        self.assertEqual(ModuleCoverageModuleInterface._meta.get_field('coverage_policy').default, 'included')
        self.assertTrue(ModuleCoverageModuleInterface._meta.get_field('coverage_reason').blank)
        for bad in ({'interface_ids': []}, {'interface_ids': [True]}, {'interface_ids': [-1]},
                    {'policy': True}, {'policy': 'invalid'}, {'reason': 'x' * 2001}):
            with self.subTest(value=bad), self.assertRaises(ValidationError):
                ModuleCoveragePolicyUpdate.model_validate({'interface_ids': [1], 'policy': 'excluded', **bad})

    def test_policy_does_not_override_computed_coverage_progress(self):
        snapshot = excluded_snapshot()
        self.assertEqual(Service.interface_coverage_status(snapshot, 2, 2, 0), 'covered')
        snapshot.module_interface.coverage_policy = 'deferred'
        for target, completed, deferred, status in ((2, 2, 0, 'covered'), (2, 1, 0, 'partial'),
                                                    (0, 0, 1, 'deferred'), (0, 0, 0, 'uncovered')):
            self.assertEqual(Service.interface_coverage_status(snapshot, target, completed, deferred), status)
        self.assertNotIn('excluded', ModuleCoverageInterfaceCoverageStatus.values)
        self.assertIn('excluded', ModuleCoveragePolicy.values)

    def run_update(self, ids, policy, reason, snapshots, allowed=True):
        source = MagicMock()
        source.filter.return_value = source
        source.select_related.return_value = snapshots
        relations = {item.module_interface_id: item.module_interface for item in snapshots}
        with ExitStack() as stack:
            stack.enter_context(patch.object(ModuleCoverageInterfaceSnapshot.objects, 'filter', return_value=source))
            users = stack.enter_context(patch.object(UserQuerySelector, 'user'))
            users.return_value.filter.return_value.first.return_value = SimpleNamespace(id=7)
            stack.enter_context(patch.object(ProjectProductScopeService, 'has_project_product', return_value=allowed))
            stack.enter_context(patch.object(ProjectProduct.objects, 'select_for_update'))
            lock = stack.enter_context(patch.object(ModuleCoverageModuleInterface.objects, 'select_for_update'))
            lock.return_value.get.side_effect = lambda id: relations[id]
            stack.enter_context(patch.object(Service, 'adopt_legacy_module_interface_state', side_effect=lambda item: item))
            update = stack.enter_context(patch.object(ModuleCoverageModuleInterface.objects, 'filter'))
            update.return_value.update.return_value = len(relations)
            result = Service.update_interface_policy.__wrapped__(Service, ids, policy, reason, 7)
            return result, update.return_value.update.call_args.kwargs

    def test_manual_exclusion_and_restore_only_update_policy_fields(self):
        result, updates = self.run_update([1, 1], 'excluded', '  专用集成接口  ', [excluded_snapshot()])
        self.assertEqual(result['interface_ids'], [1])
        self.assertEqual(updates['coverage_reason'], '专用集成接口')
        self.assertEqual(set(updates), {'coverage_policy', 'coverage_reason', 'update_time'})
        for policy in ('included', 'deferred'):
            _, updates = self.run_update([1], policy, '处理说明', [excluded_snapshot()])
            self.assertEqual(updates['coverage_policy'], policy)
            self.assertEqual(updates['coverage_reason'], '处理说明')

    def test_batch_missing_or_out_of_scope_ids_reject_without_partial_update(self):
        for ids, allowed in (([1, 2], True), ([1], False)):
            with self.subTest(ids=ids, allowed=allowed), self.assertRaises(AutoApiError):
                self.run_update(ids, 'excluded', '原因', [excluded_snapshot()], allowed=allowed)

    def test_blank_exclusion_reason_rejects_before_reading_database(self):
        with patch.object(ModuleCoverageInterfaceSnapshot.objects, 'filter') as read:
            for policy in ('excluded', 'deferred'):
                with self.assertRaises(AutoApiError) as error:
                    Service.update_interface_policy.__wrapped__(Service, [1], policy, ' ', 7)
                self.assertIn('必须填写处理原因', error.exception.msg)
            read.assert_not_called()

    def test_stale_snapshot_id_does_not_update_new_current_interface(self):
        snapshot = excluded_snapshot()
        snapshot.module_interface.current_snapshot_id = 2
        with self.assertRaises(AutoApiError):
            self.run_update([1], 'excluded', '原因', [snapshot])

    def test_full_upload_rejects_excluded_graph(self):
        scan = SimpleNamespace(id=1, project_product_id=9, module_id=1, repository_key='backend',
                               branch='main', scope_type='module', summary={})
        with patch.object(Service, 'get_locked_uploading_scan', return_value=scan), \
                patch.object(Service, 'validate_module_scope'), \
                patch.object(ModuleCoverageInterfaceSnapshot.objects, 'filter') as existing, \
                patch.object(Service, 'get_or_create_module_interface', return_value=excluded_snapshot().module_interface), \
                patch.object(Service, 'adopt_legacy_module_interface_state', side_effect=lambda item: item), \
                patch.object(ModuleCoverageInterfaceSnapshot.objects, 'create') as create:
            existing.return_value.filter.return_value.first.return_value = None
            with self.assertRaises(AutoApiError) as error:
                Service.upload_interfaces.__wrapped__(Service, 1, [{
                    'source_key': 'post:/api/contracts/search', 'payload': valid_interface_payload(),
                }])
            self.assertIn('暂不处理或排除覆盖', error.exception.msg)
            create.assert_not_called()

    def test_case_upload_rejects_excluded_interface(self):
        scan = SimpleNamespace(id=1, project_product_id=9, module_id=1, repository_key='backend',
                               branch='main', scope_type='module', summary={})
        with patch.object(Service, 'get_locked_uploading_scan', return_value=scan), \
                patch.object(Service, 'validate_module_scope'), \
                patch.object(ProjectProduct.objects, 'select_for_update'), \
                patch.object(ModuleCoverageInterfaceSnapshot.objects, 'filter') as interfaces, \
                patch.object(Service, 'validate_api_case') as validate_case:
            interfaces.return_value.select_related.return_value.first.return_value = excluded_snapshot()
            with self.assertRaises(AutoApiError) as error:
                Service.upload_cases.__wrapped__(Service, 1, [{'source_key': 'scene-1', 'payload': valid_payload()}])
            self.assertIn('暂不处理或排除覆盖', error.exception.msg)
            validate_case.assert_not_called()

    def test_overview_keeps_exclusion_count_outside_denominator_and_gaps(self):
        helper = overview_helpers.ModuleCoverageOverviewTests()
        result = helper.overview([overview_helpers.module(1)], interfaces=[
            overview_helpers.interface(1, 1), overview_helpers.interface(2, 1, module_interface=excluded_snapshot().module_interface),
        ])
        self.assertEqual(result['summary']['interface_count'], 1)
        self.assertEqual(result['summary']['excluded_interface_count'], 1)
        self.assertEqual(result['interface_gap_count'], 1)

    def test_deferred_policy_stays_in_denominator_and_blocks_new_analysis(self):
        snapshot = excluded_snapshot()
        snapshot.module_interface.coverage_policy = 'deferred'
        with self.assertRaises(AutoApiError):
            Service.require_interface_included(snapshot)
        result = overview_helpers.ModuleCoverageOverviewTests().overview(
            [overview_helpers.module(1)], interfaces=[overview_helpers.interface(1, 1, module_interface=snapshot.module_interface)],
        )
        self.assertEqual(result['summary']['interface_count'], 1)
        self.assertEqual(result['summary']['excluded_interface_count'], 0)
        self.assertEqual(result['summary']['interface_coverage_rate'], 0)

    def test_charts_exclude_interface_and_its_cases_from_all_rollup_counts(self):
        root = overview_helpers.module(1)
        child = overview_helpers.module(2, root)
        for excluded_status in ('completed', 'pending_create', 'deferred'):
            with self.subTest(excluded_status=excluded_status):
                result = overview_helpers.ModuleCoverageOverviewTests().overview(
                    [root, child], interfaces=[
                        overview_helpers.interface(1, 2),
                        overview_helpers.interface(2, 2, module_interface=excluded_snapshot().module_interface),
                    ], cases=[
                        overview_helpers.case(1, 1, 2),
                        overview_helpers.case(2, 2, 2, status=excluded_status),
                    ],
                )
                for stats in [result['summary'], *result['modules']]:
                    self.assertEqual(stats['interface_count'], 1)
                    self.assertEqual(stats['excluded_interface_count'], 1)
                    self.assertEqual(stats['covered_interface_count'], 1)
                    self.assertEqual(stats['target_count'], 1)
                    self.assertEqual(stats['completed_count'], 1)
                    self.assertEqual(stats['deferred_count'], 0)
                    self.assertEqual(stats['interface_coverage_rate'], 100)
                    self.assertEqual(stats['automation_rate'], 100)

    def test_case_statistics_query_filters_excluded_policy_by_default(self):
        _, params = Service.active_cases().query.sql_with_params()
        self.assertIn(ModuleCoveragePolicy.EXCLUDED, params)
        _, history_params = Service.active_cases(include_excluded=True).query.sql_with_params()
        self.assertNotIn(ModuleCoveragePolicy.EXCLUDED, history_params)

    def test_scan_cannot_apply_previously_uploaded_analysis_after_policy_changes(self):
        path = 'src.apps.auto_api.services.module_coverage_parts.completion'
        for policy, inventory in (('excluded', False), ('deferred', False), ('excluded', True)):
            with self.subTest(policy=policy, inventory=inventory), ExitStack() as stack:
                target = excluded_snapshot(module_id=1, sync_action='unchanged')
                target.module_interface.coverage_policy = policy
                target.module_interface.removed_at = None
                target.module_interface.module_id = 1
                target.module_interface.save = MagicMock()
                scan = SimpleNamespace(id=5, project_product_id=9, module_id=1, include_descendants=False,
                                       repository_key='backend', branch='main', scope_type='module', scan_mode='full',
                                       summary={'inventory_only': inventory}, save=MagicMock(),
                                       case_snapshots=MagicMock(), interface_snapshots=MagicMock())
                scan.case_snapshots.select_related.return_value = []
                scan.interface_snapshots.select_related.return_value = [target]
                stack.enter_context(patch.object(Service, 'get_locked_uploading_scan', return_value=scan))
                stack.enter_context(patch.object(Service, 'module_ids', return_value={1}))
                stack.enter_context(patch.object(Service, 'validation', return_value={
                    'valid': True, 'resolved_interface_count': 0, 'placeholder_interface_count': 0,
                    'gap_interface_count': 0, 'interface_resolution_rate': 0,
                }))
                stack.enter_context(patch(path + '.ProjectProduct.objects.select_for_update'))
                scans = stack.enter_context(patch(path + '.ModuleCoverageScan.objects.filter'))
                scans.return_value.exists.return_value = False
                relations = stack.enter_context(patch(path + '.ModuleCoverageModuleInterface.objects'))
                relations.filter.return_value.exists.return_value = False
                relations.filter.return_value.filter.return_value = relations.filter.return_value
                locked = MagicMock()
                locked.filter.return_value = locked
                locked.select_related.return_value = locked
                locked.values_list.return_value = []
                relations.select_for_update.return_value.filter.return_value = locked
                cases = stack.enter_context(patch(path + '.ModuleCoverageCase.objects.filter'))
                current_cases = MagicMock()
                current_cases.exclude.return_value = current_cases
                current_cases.count.return_value = 0
                current_cases.values_list.return_value = []
                cases.return_value = current_cases
                result = Service.complete_scan.__wrapped__(Service, 5)
                self.assertEqual(target.module_interface.coverage_policy, policy)
                self.assertEqual(result.summary['interface_removed'], 0)
                self.assertEqual(result.summary['interface_count'], 1 if inventory else 0)
                self.assertEqual(result.summary['skipped_interface_count'], 0 if inventory else 1)
                current_cases.update.assert_not_called()

    def test_rest_and_mcp_are_change_permission_and_guest_cannot_change(self):
        path = '/api/api/module-coverage/interfaces/policy'
        match = resolve(path)
        view = match.func.cls()
        view.action = match.func.actions['post']
        user = SimpleNamespace(id=7)
        for keys, expected in (({'api.module_coverage:change'}, True), ({'api.module_coverage:read'}, False)):
            with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                    patch.object(PermissionMenuService, 'permission_keys_for_user', return_value=keys):
                request = SimpleNamespace(method='POST', path=path, data={}, query_params=QueryDict(),
                                          user=SimpleNamespace(user_obj=user))
                self.assertEqual(MenuActionPermission().has_permission(request, view), expected)
        self.assertFalse(MenuActionPermission().has_permission(
            SimpleNamespace(method='POST', path=path, data={}, query_params=QueryDict(), user=None), view))
        policy = MCP_PERMISSION_RULES['update_module_coverage_interface_policy']
        self.assertEqual(policy['permission_key'], 'api.module_coverage:change')
        self.assertFalse(policy['public'])
        self.assertEqual(_tool_operation('update_module_coverage_interface_policy'), 'update')

    async def test_authorized_mcp_discovers_exclusion_on_both_endpoints(self):
        access = AccessToken(token='test_key', client_id='coverage-test', subject='7',
                             scopes=['api.module_coverage:read', 'api.module_coverage:change'],
                             claims={'user_id': 7, 'is_super_admin': False})
        with patch.object(MangoAuthorizationMiddleware, '_access', new=AsyncMock(return_value=access)):
            for domain in (None, 'api'):
                async with Client(mcp_asgi_app(domain).fastmcp_server) as client:
                    tools = {tool.name: tool for tool in await client.list_tools()}
                tool = tools['update_module_coverage_interface_policy']
                self.assertEqual(tool.inputSchema['properties']['policy']['type'], 'string')
                self.assertIn('coverage_policy', tools['list_module_coverage_interfaces'].inputSchema['properties'])
