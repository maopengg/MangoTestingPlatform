import re
import sqlite3
from contextlib import closing
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.http import QueryDict
from django.db.backends.sqlite3.base import DatabaseWrapper
from django.test import SimpleTestCase
from django.urls import resolve

from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.services.http_permission_catalog import http_permission_catalog
from src.apps.user.services.http_permission_registry import PROJECT_MODULE_OPTION_PERMISSIONS
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService


class SharedOptionPermissionTests(SimpleTestCase):
    def allowed(self, path, grants, method='get', user=True):
        match = resolve('/api' + path)
        view = match.func.cls()
        view.action = (getattr(match.func, 'actions', None) or {}).get(method, method)
        request = SimpleNamespace(method=method.upper(), path='/api' + path, data={}, query_params=QueryDict(),
                                  user=SimpleNamespace(user_obj=SimpleNamespace(id=7)) if user else None)
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                patch.object(PermissionMenuService, 'permission_keys_for_user', return_value=set(grants)):
            return MenuActionPermission().has_permission(request, view)

    def test_each_consumer_menu_can_load_shared_navigation_with_only_its_own_operation(self):
        paths = ('/system/project/all', '/system/project/product/name', '/system/product/name',
                 '/system/product/all/module/name', '/system/module/tree', '/system/module/name')
        known = PermissionMenuService.all_permission_keys()
        for path in paths:
            metadata = next(row for row in http_permission_catalog()
                            if row['method'] == 'GET' and re.fullmatch(row['pattern'], path))
            self.assertEqual(set(metadata['permissions']), set(PROJECT_MODULE_OPTION_PERMISSIONS))
            for grant in PROJECT_MODULE_OPTION_PERMISSIONS:
                with self.subTest(path=path, grant=grant):
                    self.assertIn(grant, known)
                    self.assertTrue(self.allowed(path, {grant}))
            self.assertFalse(self.allowed(path, {'index.home:read'}))
            self.assertFalse(self.allowed(path, known, user=False))

    def test_resource_options_follow_the_using_page_not_resource_management(self):
        cases = (
            ('/api/info/name', 'api.case'),
            ('/ui/page/name', 'ui.page_steps'),
            ('/ui/page/name', 'ui.case'),
            ('/ui/page/steps/name', 'ui.case'),
            ('/pytest/product/name', 'timing.tasks'),
            ('/system/notice/name', 'timing.tasks'),
            ('/system/notice/name', 'monitoring.task'),
            ('/system/notice/name', 'api.auth_config'),
            ('/system/notice/name', 'ui.auth_config'),
        )
        for path, page in cases:
            for operation in ('read', 'add', 'change'):
                with self.subTest(path=path, page=page, operation=operation):
                    self.assertTrue(self.allowed(path, {f'{page}:{operation}'}))
            self.assertFalse(self.allowed(path, {f'{page}:remove'}))
            self.assertFalse(self.allowed(path, {'index.home:read'}))
        self.assertTrue(self.allowed('/system/notice/name', {'report:change'}))

    def test_options_do_not_grant_full_asset_or_write_access(self):
        for path, grants in (('/system/product', {'ui.page:read'}),
                             ('/system/module', {'ui.case:change'}),
                             ('/system/notice', {'timing.tasks:change'}),
                             ('/api/info', {'api.case:change'}),
                             ('/ui/page', {'ui.case:change'}),
                             ('/ui/page/steps', {'ui.case:change'}),
                             ('/pytest/product', {'timing.tasks:change'})):
            for method in ('get', 'post', 'put', 'delete'):
                with self.subTest(path=path, method=method):
                    self.assertFalse(self.allowed(path, grants, method))

    def test_guest_keeps_management_denied_while_business_options_work(self):
        grants = PermissionMenuService.guest_permission_keys()
        for path in ('/system/module/tree', '/system/project/product/name', '/system/notice/name',
                     '/api/info/name', '/ui/page/name', '/ui/page/steps/name', '/pytest/product/name'):
            self.assertTrue(self.allowed(path, grants))
        for path in ('/user/info', '/user/role', '/system/cache/data'):
            self.assertFalse(self.allowed(path, grants))

    def test_task_report_selection_does_not_grant_full_report_export(self):
        self.assertTrue(self.allowed('/system/test/suite/offline/options', {'timing.tasks:read'}))
        for path in ('/system/test/suite/offline', '/system/test/suite/offline/links'):
            self.assertFalse(self.allowed(path, {'timing.tasks:read'}, 'post'))

    def test_name_views_apply_existing_product_scope_policy(self):
        from src.apps.auto_api.api.views.api_info import ApiInfoCRUD, ApiInfoViews
        from src.apps.auto_ui.api.views.ui_page import PageCRUD, PageViews
        from src.apps.auto_ui.api.views.ui_page_steps import PageStepsCRUD, PageStepsViews

        for view_type, action, crud in ((ApiInfoViews, 'get_api_name', ApiInfoCRUD),
                                        (PageViews, 'page_name', PageCRUD),
                                        (PageStepsViews, 'get_page_steps_name', PageStepsCRUD)):
            request = SimpleNamespace(query_params=QueryDict('module_id=1&page_id=1'),
                                      user=SimpleNamespace(user_obj=SimpleNamespace(id=7)))
            scoped = Mock()
            scoped.values_list.return_value = [(1, '示例选项')]
            scoped.__iter__ = Mock(return_value=iter([]))
            with self.subTest(view=view_type.__name__), \
                    patch.object(crud, 'filter_queryset_by_data_scope', return_value=scoped) as filter_scope:
                response = getattr(view_type(), action)(request)
                self.assertEqual(response.data['code'], 200)
                self.assertIs(filter_scope.call_args.args[0], request)

    def test_resource_scope_sql_excludes_other_products_and_empty_department_scope(self):
        from src.apps.auto_api.models import ApiInfo
        from src.apps.auto_ui.models import Page, PageSteps
        from src.apps.user.services.model_crud_scope import ModelCrudDataScopePolicy

        request = SimpleNamespace(user=SimpleNamespace(user_obj=SimpleNamespace(id=7)))
        compiler = DatabaseWrapper({'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}, alias='option_sql')
        with closing(sqlite3.connect(':memory:')) as database, \
                patch.object(ModelCrudDataScopePolicy, '_unrestricted', return_value=False):
            for model in (ApiInfo, Page, PageSteps):
                table = model._meta.db_table
                database.execute(f'CREATE TABLE "{table}" (id INTEGER PRIMARY KEY, project_product_id INTEGER)')
                database.executemany(f'INSERT INTO "{table}" VALUES (?, ?)', [(1, 2), (2, 3)])
                for allowed, expected in (({2}, [(1,)]), (set(), [])):
                    with self.subTest(model=model.__name__, allowed=allowed), \
                            patch.object(ModelCrudDataScopePolicy, '_allowed_ids', return_value=allowed):
                        queryset = ModelCrudDataScopePolicy.filter_queryset(model, request, model.objects.all(), set())
                        if not allowed:
                            self.assertTrue(queryset.query.is_empty())
                            continue
                        sql, params = queryset.order_by('id').values_list('id').query.get_compiler(connection=compiler).as_sql()
                        self.assertEqual(database.execute(sql.replace('%s', '?'), params).fetchall(), expected)

    def test_notice_names_do_not_query_or_leak_other_products(self):
        from src.apps.test_center.selectors.notice_group import NoticeGroupOptionSelector

        user = SimpleNamespace(id=7)
        with patch.object(ProjectProductScopeService, 'has_project_product', return_value=False), \
                patch('src.apps.test_center.selectors.notice_group.ProjectProduct.objects') as products, \
                patch('src.apps.test_center.selectors.notice_group.NoticeGroup.objects') as notices:
            for product in (2, None, 'invalid'):
                self.assertEqual(NoticeGroupOptionSelector.options(user, product), [])
            products.filter.assert_not_called()
            notices.filter.assert_not_called()
        with patch.object(ProjectProductScopeService, 'has_project_product', return_value=True), \
                patch('src.apps.test_center.selectors.notice_group.ProjectProduct.objects') as products, \
                patch('src.apps.test_center.selectors.notice_group.NoticeGroup.objects') as notices:
            products.filter.return_value.values_list.return_value.first.return_value = 3
            notices.filter.return_value.values.return_value = [{'id': 5, 'name': '示例通知组'}]
            self.assertEqual(NoticeGroupOptionSelector.options(user, 2), [{'id': 5, 'name': '示例通知组'}])
            products.filter.assert_called_once_with(id=2)
            notices.filter.assert_called_once_with(project_id=3)
            notices.filter.return_value.values.assert_called_once_with('id', 'name')
