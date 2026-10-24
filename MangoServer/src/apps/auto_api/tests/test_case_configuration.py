from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.http import QueryDict
from django.test import SimpleTestCase

from src.apps.auto_api.api.views.api_case import ApiCaseViews
from src.apps.auto_api.selectors.case_configuration import ApiCaseConfigurationSelector
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService


class ApiCaseConfigurationTests(SimpleTestCase):
    def test_single_configuration_filter_batches_and_combines_choices_with_and(self):
        queryset = MagicMock()
        queryset.order_by.return_value.values_list.return_value.iterator.return_value = iter(range(1, 206))

        def summaries(ids, **kwargs):
            return {case_id: {'has_sql': case_id in (1, 205), 'has_data_factory': case_id == 205} for case_id in ids}

        user = SimpleNamespace(id=7)
        with patch.object(ApiCaseConfigurationSelector, 'collect', side_effect=summaries) as collect:
            ApiCaseConfigurationSelector.filter_queryset(queryset, ['has_sql', 'has_data_factory'], user=user)
        self.assertEqual([len(call.args[0]) for call in collect.call_args_list], [200, 5])
        queryset.filter.assert_called_once_with(pk__in=[205])

    def test_negative_filter_and_unrestricted_selection(self):
        queryset = MagicMock()
        queryset.order_by.return_value.values_list.return_value.iterator.return_value = iter([1, 2])
        with patch.object(ApiCaseConfigurationSelector, 'collect', return_value={
            1: {'has_sql': True, 'has_data_factory': False}, 2: {'has_sql': False, 'has_data_factory': True},
        }) as collect:
            ApiCaseConfigurationSelector.filter_queryset(queryset, ['no_sql'], user=None)
            queryset.filter.assert_called_once_with(pk__in=[2])
            collect.reset_mock()
            self.assertIs(ApiCaseConfigurationSelector.filter_queryset(queryset, [], user=None), queryset)
            self.assertIs(ApiCaseConfigurationSelector.filter_queryset(queryset, ['has_sql', 'no_sql'], user=None), queryset.none.return_value)
            collect.assert_not_called()

    def test_configuration_search_rejects_invalid_choices(self):
        from src.apps.auto_api.api.serializers.api_case import ApiCaseConfigurationFilterQuery
        query = ApiCaseConfigurationFilterQuery(data={'execution_configuration': ['has_sql', 'no_data_factory']})
        self.assertTrue(query.is_valid())
        self.assertEqual(query.validated_data['execution_configuration'], ['has_sql', 'no_data_factory'])
        self.assertFalse(ApiCaseConfigurationFilterQuery(data={'execution_configuration': ['unknown']}).is_valid())

    def collect(self, include_content=False):
        cases = MagicMock()
        cases.values.return_value = [
            {'id': 1, 'name': '用例一', 'front_sql': [{'value': 'select 1'}],
             'posterior_sql': [], 'front_public': [8]},
            {'id': 2, 'name': '无配置', 'front_sql': [], 'posterior_sql': [], 'front_public': []},
        ]
        parameter = {'id': 11, 'name': '正常场景', 'case_detailed__case_id': 1,
                     'case_detailed__case_sort': 1, 'case_detailed__api_info__name': '查询接口',
                     'front_sql': [], 'posterior_sql': [{'value': 'delete from example_table'}],
                     'ass_sql': [{'actual': 'select count(*) from example_table'}]}
        factories = [
            {'id': 20, 'source_type': 1, 'source_id': 1, 'stage': 2, 'status': 1, 'template__name': '订单模板'},
            {'id': 21, 'source_type': 3, 'source_id': 11, 'stage': 3, 'status': 0, 'template__name': '清理模板'},
        ]
        with (
            patch.object(ApiCaseConfigurationSelector, 'scoped_cases', return_value=cases),
            patch('src.apps.auto_api.selectors.case_configuration.ApiCaseDetailedParameter.objects.filter') as params,
            patch('src.apps.auto_api.selectors.case_configuration.ApiPublic.objects.filter') as public,
            patch('src.apps.auto_api.selectors.case_configuration.ApiCaseRelease.objects.filter') as releases,
            patch('src.apps.auto_api.selectors.case_configuration.DataFactoryQuerySelector.data_factory_case_config') as factory,
        ):
            params.return_value.order_by.return_value.values.return_value = [parameter]
            public.return_value.values.return_value = [{'id': 8, 'status': 1}]
            releases.return_value.order_by.return_value.values.return_value = []
            factory.return_value.filter.return_value.order_by.return_value.values.return_value = factories
            result = ApiCaseConfigurationSelector.collect([1, 2], user=SimpleNamespace(id=7), include_content=include_content)
            params.assert_called_once()
            factory.assert_called_once()
            return result

    def test_configuration_follows_active_publication_state_and_never_falls_back_to_editing(self):
        cases = MagicMock()
        cases.values.return_value = [{'id': 1, 'name': '未发布'}, {'id': 2, 'name': '预发布'}, {'id': 3, 'name': '已发布'}]
        pending = {'api_case': {'front_sql': [{'value': 'select 2'}]}, 'dependencies': {'data_factory_configs': []}}
        published = {'api_case': {'front_sql': []}, 'dependencies': {'data_factory_configs': [
            {'id': 9, 'source_type': 1, 'source_id': 3, 'template': 7, 'status': 0},
        ]}}
        with patch.object(ApiCaseConfigurationSelector, 'scoped_cases', return_value=cases), patch(
            'src.apps.auto_api.selectors.case_configuration.ApiCaseRelease.objects.filter',
        ) as releases, patch.object(ApiCaseConfigurationSelector, '_collect_editing', return_value={
            1: {'id': 1, 'sql_count': 90, 'data_factory_count': 0, 'items': []},
        }) as editing:
            releases.return_value.order_by.return_value.values.return_value = [
                {'api_case_id': 2, 'status': 'published', 'revision_id': 20, 'revision__payload': published},
                {'api_case_id': 2, 'status': 'prepublished', 'revision_id': 21, 'revision__payload': pending},
                {'api_case_id': 3, 'status': 'published', 'revision_id': 30, 'revision__payload': published},
            ]
            result = ApiCaseConfigurationSelector.collect([1, 2, 3], user=SimpleNamespace(id=7), include_content=True)
        editing.assert_called_once_with([1], user=SimpleNamespace(id=7), include_content=True)
        self.assertEqual(result[1]['publication_status'], 'unpublished')
        self.assertEqual(result[2]['publication_status'], 'prepublished')
        self.assertEqual(result[2]['revision_id'], 21)
        self.assertEqual(result[2]['sql_count'], 1)
        self.assertEqual(result[2]['items'][0]['configuration']['value'], 'select 2')
        self.assertEqual(result[3]['publication_status'], 'published')
        self.assertEqual(result[3]['sql_count'], 0)
        self.assertEqual(result[3]['data_factory_count'], 1)
        self.assertFalse(result[3]['items'][0]['enabled'])

    def test_frozen_summary_and_details_use_the_same_counts_and_global_references(self):
        payload = {'api_case': {'front_sql': [{'sql': 'select 1'}], 'front_public': [8]},
                   'api_case_detailed': [{'api_case_detailed_parameter': [{'ass_sql': [{'actual': 'select 2'}]}]}],
                   'dependencies': {'data_factory_configs': [{'template': 3, 'status': 1}]}}
        args = {'public_sql': [{'id': 8, 'status': 1}, {'id': 9, 'status': 1}]}
        summary = ApiCaseConfigurationSelector.from_payload(1, 'Case', payload, **args)
        details = ApiCaseConfigurationSelector.from_payload(1, 'Case', payload, include_content=True, **args)
        self.assertEqual(summary, {key: value for key, value in details.items() if key != 'items'})
        self.assertEqual(summary['sql_count'], 3)
        self.assertEqual(summary['data_factory_count'], 1)
        self.assertEqual(details['items'][-1]['configuration']['global_variable_id'], 8)

    def test_batch_summary_includes_all_levels_without_returning_configuration(self):
        result = self.collect()
        self.assertEqual(result[1]['sql_count'], 4)
        self.assertEqual(result[1]['data_factory_count'], 2)
        self.assertTrue(result[1]['has_sql'])
        self.assertTrue(result[1]['has_data_factory'])
        self.assertFalse(result[2]['has_sql'])
        self.assertFalse(result[2]['has_data_factory'])
        self.assertNotIn('items', result[1])
        self.assertNotIn('select', str(result))

    def test_details_preserve_locations_contents_and_disabled_factory(self):
        items = self.collect(include_content=True)[1]['items']
        self.assertEqual(items[0]['configuration']['value'], 'select 1')
        self.assertEqual(items[0]['location'], '用例 / 前置 SQL')
        self.assertIn('正常场景 / 后置 SQL', items[1]['location'])
        self.assertIn('SQL 断言', items[2]['location'])
        self.assertEqual(items[-1]['configuration']['template__name'], '清理模板')
        self.assertFalse(items[-1]['enabled'])
        self.assertNotIn('value', items[3]['configuration'])

    def test_scoped_cases_filter_by_product_and_deny_anonymous(self):
        user = SimpleNamespace(id=7)
        with (
            patch('src.apps.auto_api.selectors.case_configuration.ApiCase.objects.filter') as cases,
            patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False),
            patch.object(ProjectProductScopeService, 'can_view_all_project_data', return_value=False),
            patch.object(ProjectProductScopeService, 'project_product_ids_for_user', return_value={3}),
        ):
            ApiCaseConfigurationSelector.scoped_cases([1, 2], user)
            cases.return_value.filter.assert_called_once_with(project_product_id__in={3})
            ApiCaseConfigurationSelector.scoped_cases([1], None)
            cases.return_value.none.assert_called_once()

    def test_missing_or_unscoped_ids_do_not_query_dependencies(self):
        cases = MagicMock()
        cases.values.return_value = []
        with (
            patch.object(ApiCaseConfigurationSelector, 'scoped_cases', return_value=cases),
            patch('src.apps.auto_api.selectors.case_configuration.ApiCaseDetailedParameter.objects.filter') as params,
        ):
            self.assertEqual(ApiCaseConfigurationSelector.collect([9], user=SimpleNamespace(id=7)), {})
            params.assert_not_called()

    def test_view_uses_page_permission_for_counts_and_detail_permission_for_contents(self):
        for action, required in (('configuration_summary', 'api.case'), ('configuration_details', 'api.case:detail')):
            view = ApiCaseViews()
            view.action = action
            request = SimpleNamespace(method='GET', path='/api/api/case/configuration/summary', data={},
                                      query_params=QueryDict(), user=SimpleNamespace(user_obj=SimpleNamespace(id=7)))
            with (
                patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False),
                patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={required}),
            ):
                self.assertTrue(MenuActionPermission().has_permission(request, view))
            with (
                patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False),
                patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'index.home'}),
            ):
                self.assertFalse(MenuActionPermission().has_permission(request, view))

    def test_detail_not_found_and_pagination(self):
        request = SimpleNamespace(query_params=QueryDict('id=1&page=2&pageSize=1'),
                                  user=SimpleNamespace(user_obj=SimpleNamespace(id=7)))
        with patch.object(ApiCaseConfigurationSelector, 'collect', return_value={}):
            self.assertNotEqual(ApiCaseViews().configuration_details(request).data['code'], 0)
        with patch.object(ApiCaseConfigurationSelector, 'collect', return_value={1: {'id': 1, 'items': ['one', 'two']}}):
            result = ApiCaseViews().configuration_details(request).data
            self.assertEqual(result['data']['items'], ['two'])
            self.assertEqual(result['totalSize'], 2)

    def test_query_validation_rejects_oversized_and_invalid_id_lists(self):
        from src.apps.auto_api.api.serializers.api_case import ApiCaseConfigurationSummaryQuery
        self.assertFalse(ApiCaseConfigurationSummaryQuery(data={'case_ids': [0]}).is_valid())
        self.assertFalse(ApiCaseConfigurationSummaryQuery(data={'case_ids': list(range(1, 202))}).is_valid())
