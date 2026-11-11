from types import SimpleNamespace
from datetime import datetime
from unittest.mock import Mock, patch

from django.http import QueryDict
from django.test import SimpleTestCase

from src.apps.auto_api.api.views.api_headers import ApiHeadersViews
from src.apps.auto_api.api.serializers.api_info import ApiInfoBoundCaseSerializers
from src.apps.auto_api.api.views.api_pulic import ApiPublicViews
from src.apps.auto_api.selectors.configuration_references import ApiConfigurationReferenceSelector
from src.apps.auto_ui.api.views.ui_public import UiPublicViews
from src.apps.user.services.http_permission_registry import permission_for_view
from src.common.responses.response_msg import RESPONSE_MSG_0210
from src.common.utils.json_references import collect_json_references, reference_case_page


class JsonRows:
    db = 'default'

    def __init__(self, rows):
        self.rows = rows
        self.columns = None

    def values_list(self, *columns):
        self.columns = columns
        return self

    def iterator(self, chunk_size):
        return iter(self.rows)


class ConfigurationReferenceTests(SimpleTestCase):
    def collect(self, rows, ids):
        with patch('src.common.utils.json_references.connections', {'default': SimpleNamespace(vendor='sqlite')}):
            return collect_json_references(rows, 'id', 'front_public', ids)

    def test_repeated_numeric_and_string_bindings_count_each_case_once(self):
        rows = JsonRows([(11, [1, 1, '1', 2]), (12, ['1']), (13, []), (14, None),
                         (15, [True, {}, 'bad', ' 1', 1.0]), (16, {'id': 1})])
        self.assertEqual(self.collect(rows, [1, 2, 3]), {1: {11, 12}, 2: {11}, 3: set()})
        self.assertEqual(rows.columns, ('id', 'front_public'))

    def test_empty_page_never_reads_cases(self):
        rows = Mock()
        self.assertEqual(self.collect(rows, []), {})
        rows.values_list.assert_not_called()

    def test_mysql_uses_one_overlap_predicate_for_all_current_page_assets(self):
        rows = Mock(db='default')
        rows.annotate.return_value.filter.return_value.values_list.return_value.iterator.return_value = iter([])
        with patch('src.common.utils.json_references.connections', {'default': SimpleNamespace(vendor='mysql')}):
            self.assertEqual(collect_json_references(rows, 'id', 'front_public', [1, 2]), {1: set(), 2: set()})
        predicate = rows.annotate.call_args.kwargs['_reference_match']
        self.assertEqual(predicate.extra['function'], 'JSON_OVERLAPS')
        self.assertEqual(set(predicate.source_expressions[1].value), {1, 2, '1', '2'})

    def test_header_case_and_parameter_bindings_are_merged_and_deduplicated(self):
        cases = Mock()
        parameters = Mock()
        with patch('src.apps.auto_api.selectors.configuration_references.ApiCaseDetailedParameter.objects.filter',
                   return_value=parameters) as query, patch(
            'src.apps.auto_api.selectors.configuration_references.collect_json_references',
            side_effect=[{1: {10}, 2: set()}, {1: {10, 11}, 2: {11}}],
        ) as collect:
            self.assertEqual(ApiConfigurationReferenceSelector.headers(cases, [1, 2]), {1: {10, 11}, 2: {11}})
        query.assert_called_once_with(case_detailed__case_id__in=cases.values.return_value)
        self.assertEqual(collect.call_args.args[1:3], ('case_detailed__case_id', 'headers'))

    def test_public_selector_only_reads_explicit_front_public_not_defaults_or_auth(self):
        cases = JsonRows([(11, [4]), (12, [])])
        with patch('src.common.utils.json_references.connections', {'default': SimpleNamespace(vendor='sqlite')}):
            self.assertEqual(ApiConfigurationReferenceSelector.public_variables(cases, [4]), {4: {11}})
        self.assertEqual(cases.columns, ('id', 'front_public'))

    def setup_view(self, view_type, query_string, permitted_count=2):
        view = view_type()
        assets = Mock()
        assets.filter.return_value.count.return_value = permitted_count
        assets.filter.return_value.exists.return_value = permitted_count > 0
        cases = Mock()
        view._reference_scope = Mock(side_effect=lambda model, request: assets if model is view.model else cases)
        view.reference_selector = Mock(return_value={1: {10, 11}, 2: set()})
        request = SimpleNamespace(query_params=QueryDict(query_string))
        return view, request, cases

    def test_counts_are_bounded_deduplicated_and_not_returned_for_out_of_scope_assets(self):
        for view_type in (ApiPublicViews, ApiHeadersViews, UiPublicViews):
            view, request, cases = self.setup_view(view_type, 'ids=1,2,1')
            self.assertEqual(view.reference_counts(request).data['data'], {'1': 2, '2': 0})
            view.reference_selector.assert_called_once_with(cases, [1, 2])
            view, request, _ = self.setup_view(view_type, 'ids=1,2', permitted_count=1)
            self.assertEqual(view.reference_counts(request).data['code'], RESPONSE_MSG_0210[0])
            view.reference_selector.assert_not_called()

    def test_bad_ids_are_rejected_before_querying(self):
        for value in ('', '0', '-1', 'bad', ','.join(map(str, range(1, 202)))):
            view, request, _ = self.setup_view(ApiPublicViews, f'ids={value}')
            response = view.reference_counts(request)
            self.assertNotEqual(response.data.get('code'), 200)
            view._reference_scope.assert_not_called()

    def test_details_apply_asset_and_case_scope_and_forward_pagination(self):
        for view_type in (ApiPublicViews, ApiHeadersViews, UiPublicViews):
            view, request, cases = self.setup_view(view_type, 'id=1&page=2&pageSize=20')
            with patch('src.common.responses.configuration_references.reference_case_page',
                       return_value=([{'case_id': 11}], 21)) as read:
                response = view.reference_cases(request)
            read.assert_called_once_with(cases, {10, 11}, 2, 20)
            self.assertEqual(response.data['data'], [{'case_id': 11}])
            self.assertEqual(response.data['totalSize'], 21)
            view, request, _ = self.setup_view(view_type, 'id=1', permitted_count=0)
            self.assertEqual(view.reference_cases(request).data['code'], RESPONSE_MSG_0210[0])
            view.reference_selector.assert_not_called()

    def test_reference_endpoints_use_source_menu_read_permissions(self):
        for view_type, menu in ((ApiPublicViews, 'api.public'), (ApiHeadersViews, 'api.headers'),
                                (UiPublicViews, 'ui.public')):
            for action in ('reference_counts', 'reference_cases'):
                self.assertEqual(permission_for_view(view_type(), action, 'get'), f'{menu}:read')
                self.assertIsNone(permission_for_view(view_type(), action, 'post'))

    def test_detail_rows_select_only_page_and_preload_people(self):
        queryset = Mock()
        cases = queryset.filter.return_value.order_by.return_value
        cases.count.return_value = 41
        cases.select_related.return_value.only.return_value.__getitem__ = Mock(return_value=[])
        self.assertEqual(reference_case_page(queryset, {1, 2}, 2, 20), ([], 41))
        queryset.filter.assert_called_once_with(id__in={1, 2})
        cases.select_related.assert_called_once_with('project_product', 'case_people', 'update_user')
        cases.select_related.return_value.only.return_value.__getitem__.assert_called_once_with(slice(20, 40))

    def test_reference_rows_include_scene_tags_without_deferred_field_queries(self):
        queryset = Mock()
        cases = queryset.filter.return_value.order_by.return_value
        cases.count.return_value = 1
        row = SimpleNamespace(id=11, name='Example', scenario_tags=[0, 2], case_people_id=None,
                              update_user_id=None, update_time=datetime(2026, 11, 11, 10, 20, 30),
                              project_product_id=1, project_product=SimpleNamespace(name='Product'))
        cases.select_related.return_value.only.return_value.__getitem__ = Mock(return_value=[row])
        rows, count = reference_case_page(queryset, {11}, 1, 20)
        self.assertEqual(count, 1)
        self.assertEqual(rows[0]['scenario_tags'], [0, 2])
        self.assertIn('scenario_tags', cases.select_related.return_value.only.call_args.args)

    def test_bound_case_serializer_exposes_the_same_scene_tag_values(self):
        self.assertIn('scenario_tags', ApiInfoBoundCaseSerializers.Meta.fields)
        field = ApiInfoBoundCaseSerializers().fields['scenario_tags']
        self.assertEqual(field.to_representation([0, 2]), [0, 2])
