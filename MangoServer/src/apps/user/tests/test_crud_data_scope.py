import sqlite3
from contextlib import closing
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.apps import apps
from django.db.backends.sqlite3.base import DatabaseWrapper
from django.http import QueryDict
from django.test import SimpleTestCase

from src.apps.auto_api.models import ApiCase, ApiCaseDetailed, ApiInfo
from src.apps.user.constants import RELATED_PRODUCT_SCOPE_PATHS
from src.apps.user.services.authorization.model_crud_scope import ModelCrudDataScopePolicy as Policy
from src.apps.user.services.authorization.permission import ProjectProductScopeService


class CrudDataScopeTests(SimpleTestCase):

    def test_product_authorization_is_reused_only_within_the_same_request(self):
        request = SimpleNamespace(user=SimpleNamespace(user_obj=SimpleNamespace(id=7)))
        with patch.object(Policy, '_unrestricted', return_value=False), \
                patch.object(ProjectProductScopeService, 'project_product_ids_for_user', return_value={2}) as lookup:
            self.assertTrue(Policy.has_data_permission(ApiInfo, request, {'project_product': 2}, set()))
            Policy.filter_queryset(ApiInfo, request, ApiInfo.objects.all(), set())
            self.assertFalse(Policy.has_data_permission(ApiInfo, request, {'project_product': 3}, set()))
            lookup.assert_called_once()
            lookup.return_value = set()
            new_request = SimpleNamespace(user=request.user)
            self.assertFalse(Policy.has_data_permission(ApiInfo, new_request, {'project_product': 2}, set()))
            self.assertEqual(lookup.call_count, 2)
    def setUp(self):
        from src.apps.user.tests.permission_fixtures import install_legacy_endpoint_snapshot
        install_legacy_endpoint_snapshot(self)
        self.request = SimpleNamespace(method='PUT', data={}, query_params=QueryDict(),
                                       user=SimpleNamespace(user_obj=SimpleNamespace(id=7)))
        unrestricted = patch.object(Policy, '_unrestricted', return_value=False)
        unrestricted.start()
        self.addCleanup(unrestricted.stop)

    def test_all_declared_parent_scope_paths_are_valid_orm_queries(self):
        for label, paths in RELATED_PRODUCT_SCOPE_PATHS.items():
            model = apps.get_model(label)
            for path in paths:
                with self.subTest(label=label, path=path):
                    # Constructing a query resolves every relationship without executing SQL.
                    self.assertIn('SELECT', str(model.objects.filter(**{f'{path}__in': [1]}).query))

    def test_child_lists_filter_by_their_parent_product(self):
        queryset = Mock()
        with patch.object(Policy, '_allowed_ids', return_value=[11, 12]):
            Policy.filter_queryset(ApiCaseDetailed, self.request, queryset, set())
        predicate = queryset.filter.call_args.args[0]
        self.assertEqual(predicate.children, [('case__project_product_id__in', [11, 12])])

    def test_child_creation_cannot_attach_to_an_inaccessible_parent(self):
        self.request.method = 'POST'
        with patch.object(Policy, 'filter_queryset') as visible, patch.object(ApiCase.objects, 'filter'):
            visible.return_value.exists.return_value = False
            self.assertFalse(Policy.has_data_permission(ApiCaseDetailed, self.request, {'case': 9}, set()))
            self.assertFalse(Policy.has_data_permission(ApiCaseDetailed, self.request, {}, set()))
            visible.return_value.exists.return_value = True
            self.assertTrue(Policy.has_data_permission(ApiCaseDetailed, self.request, {'case': 9}, set()))

    def test_direct_and_batch_ids_must_all_be_visible(self):
        self.request.query_params = QueryDict('id[]=1&id[]=2')
        with patch.object(Policy, 'has_data_permission', return_value=True), \
                patch.object(ApiCaseDetailed.objects, 'filter'), patch.object(Policy, 'filter_queryset') as visible:
            visible.return_value.count.return_value = 1
            self.assertFalse(Policy.has_request_permission(ApiCaseDetailed, self.request, set()))
            visible.return_value.count.return_value = 2
            self.assertTrue(Policy.has_request_permission(ApiCaseDetailed, self.request, set()))

    def test_instance_checks_use_the_actual_parent_model(self):
        parent = ApiCase(id=4, project_product_id=11)
        with patch.object(Policy, 'has_data_permission', return_value=True) as check:
            self.assertTrue(Policy.has_instance_permission(ApiCaseDetailed, self.request, parent, set()))
        self.assertIs(check.call_args.args[0], ApiCase)

    def test_get_id_filters_only_reject_existing_inaccessible_records(self):
        self.request.method = 'GET'
        for query in ('id=999', 'id[]=1&id[]=999', 'id[]=1&id[]=1', 'id[]=1&id=1'):
            for inaccessible in (False, True):
                with self.subTest(query=query, inaccessible=inaccessible), \
                        patch.object(Policy, 'has_data_permission', return_value=True), \
                        patch.object(ApiInfo.objects, 'filter') as requested, \
                        patch.object(Policy, 'filter_queryset') as visible:
                    self.request.query_params = QueryDict(query)
                    requested.return_value.exclude.return_value.exists.return_value = inaccessible
                    self.assertEqual(Policy.has_request_permission(ApiInfo, self.request, set()), not inaccessible)
                    requested.return_value.exclude.assert_called_once_with(pk__in=visible.return_value.values.return_value)
                    visible.return_value.values.assert_called_once_with('pk')
                    requested.return_value.count.assert_not_called()
                    visible.return_value.count.assert_not_called()

    def test_write_requests_still_require_all_requested_records_to_be_visible(self):
        for method in ('PUT', 'PATCH', 'DELETE'):
            for count in (0, 1, 2):
                with self.subTest(method=method, visible_count=count), \
                        patch.object(Policy, 'has_data_permission', return_value=True), \
                        patch.object(ApiInfo.objects, 'filter') as requested, \
                        patch.object(Policy, 'filter_queryset') as visible:
                    self.request.method = method
                    self.request.query_params = QueryDict('id[]=1&id[]=999')
                    visible.return_value.count.return_value = count
                    self.assertEqual(Policy.has_request_permission(ApiInfo, self.request, set()), count == 2)
                    requested.return_value.exclude.assert_not_called()

    def test_get_missing_id_does_not_bypass_an_explicit_product_scope_denial(self):
        self.request.method = 'GET'
        self.request.query_params = QueryDict('id=999&project_product=2')
        with patch.object(Policy, 'has_data_permission', return_value=False), \
                patch.object(ApiInfo.objects, 'filter') as requested:
            self.assertFalse(Policy.has_request_permission(ApiInfo, self.request, set()))
            requested.assert_not_called()

    def test_api_info_missing_id_returns_empty_list_but_still_requires_read_permission(self):
        from rest_framework.test import APIRequestFactory, force_authenticate
        from src.apps.auto_api.api.views.api_info import ApiInfoCRUD
        from src.apps.user.services.authorization.permission import AuthUserContext, PermissionMenuService, ProjectProductScopeService

        user = SimpleNamespace(id=31, role_id=10, name='测试用户', username='audit@example.com', is_super_admin=False)
        for grants, product_allowed, expected in (({'api.info:read'}, True, 200),
                                                   ({'index.home:read'}, True, 300),
                                                   ({'api.info:read'}, False, 300)):
            with self.subTest(grants=grants, product_allowed=product_allowed), \
                    patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                    patch.object(PermissionMenuService, 'permission_keys_for_user', return_value=grants), \
                    patch.object(ProjectProductScopeService, 'can_view_all_project_data', return_value=False), \
                    patch.object(ProjectProductScopeService, 'project_product_ids_for_user', return_value={2} if product_allowed else set()), \
                    patch.object(ApiInfo.objects, 'filter', return_value=ApiInfo.objects.none()):
                request = APIRequestFactory().get('/api/api/info', {'id': 999, 'project_product': 2, 'page': 1, 'pageSize': 20})
                force_authenticate(request, user=AuthUserContext(user))
                response = ApiInfoCRUD.as_view()(request)
                self.assertEqual(response.data['code'], expected)
                if expected == 200:
                    self.assertEqual(response.data['data'], [])

    def test_invalid_primary_key_filter_does_not_bypass_permission_checks(self):
        self.request.method = 'GET'
        self.request.query_params = QueryDict('id=invalid')
        with patch.object(Policy, 'has_data_permission', return_value=True), \
                patch.object(ApiInfo.objects, 'filter', side_effect=ValueError):
            self.assertFalse(Policy.has_request_permission(ApiInfo, self.request, set()))

    def test_get_scope_sql_distinguishes_absent_and_inaccessible_rows(self):
        compiler_connection = DatabaseWrapper({'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'},
                                             alias='scope_sql')
        # 独立内存表验证实际范围查询，不使用平台数据库或执行迁移。
        with closing(sqlite3.connect(':memory:')) as database:
            database.execute('CREATE TABLE api_info (id INTEGER PRIMARY KEY, project_product_id INTEGER NOT NULL)')
            database.executemany('INSERT INTO api_info VALUES (?, ?)', [(1, 2), (2, 3)])
            for ids, expected in (([999], []), ([1, 999], []), ([1, 1], []), ([2], [(2,)]), ([1, 2, 999], [(2,)])):
                with self.subTest(ids=ids), patch.object(Policy, '_allowed_ids', return_value={2}):
                    requested = ApiInfo.objects.filter(pk__in=ids)
                    visible = Policy.filter_queryset(ApiInfo, self.request, requested, set())
                    inaccessible = requested.exclude(pk__in=visible.values('pk')).values_list('pk')[:1]
                    sql, params = inaccessible.query.get_compiler(connection=compiler_connection).as_sql()
                    self.assertEqual(database.execute(sql.replace('%s', '?'), params).fetchall(), expected)
