from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from src.apps.auto_api.api.views.api_case import ApiCaseCRUD
from src.apps.auto_ui.api.views.ui_case import UiCaseCRUD
from src.apps.functional_test.api.views.case import ManualTestCaseCRUD
from src.apps.functional_test.api.views.suite import ManualTestSuiteCRUD
from src.apps.test_center.api.views.test_suite_details import TestSuiteDetailsCRUD
from src.common.responses.model_crud import ModelCRUD


class QueryFilterParsingTests(SimpleTestCase):
    views = (ApiCaseCRUD, UiCaseCRUD, ManualTestCaseCRUD, ManualTestSuiteCRUD, TestSuiteDetailsCRUD)

    def test_all_custom_lists_preserve_date_time_bounds(self):
        for view_class in self.views:
            view = view_class()
            for lookup in ('gt', 'gte', 'lt', 'lte'):
                key = 'create_time__' + lookup
                with self.subTest(view=view_class.__name__, key=key):
                    parsed = view.parse_model_query_filter(key, ['2026-11-18T00:00:00+08:00'])
                    self.assertEqual(list(parsed), [key])
                    queryset = view.model.objects.filter(**parsed)
                    self.assertEqual(queryset.query.where.children[0].lookup_name, lookup)

    def test_all_custom_lists_support_repeated_and_csv_ranges(self):
        for view_class in self.views:
            view = view_class()
            for values in (['2026-11-17,2026-11-18'], ['2026-11-17', '2026-11-18']):
                with self.subTest(view=view_class.__name__, values=values):
                    key = 'create_time__date__range'
                    parsed = view.parse_model_query_filter(key, values)
                    self.assertEqual(parsed, {key: ['2026-11-17', '2026-11-18']})
                    self.assertEqual(view.model.objects.filter(**parsed).query.where.children[0].lookup_name, 'range')

    def test_invalid_range_reports_field_format_error_before_orm(self):
        view = ApiCaseCRUD()
        for values in (['one'], ['one,two,three'], ['', 'two']):
            with self.subTest(values=values), self.assertRaises(ValidationError) as error:
                view.parse_model_query_filter('create_time__range', values)
            self.assertEqual(error.exception.detail['create_time__range'][0].code, 'invalid')

    def test_plain_text_stays_fuzzy_but_dates_numbers_and_relations_do_not(self):
        view = ApiCaseCRUD()
        for key, value, expected_key in (
            ('name', 'example', 'name__contains'),
            ('case_people__name', 'example', 'case_people__name__contains'),
            ('case_people', '1', 'case_people'),
            ('level', '1', 'level'),
            ('create_time', '2026-11-18T00:00:00+08:00', 'create_time'),
        ):
            with self.subTest(key=key):
                parsed = view.parse_model_query_filter(key, [value])
                self.assertEqual(parsed, {expected_key: value})
                view.model.objects.filter(**parsed)

    def test_in_null_and_explicit_text_filters_preserve_semantics(self):
        view = ApiCaseCRUD()
        for key, values, expected in (
            ('module__in', ['1, 2', '3'], {'module__in': ['1', '2', '3']}),
            ('module__in', [], {}),
            ('module__isnull', ['true'], {'module__isnull': True}),
            ('module__isnull', ['false'], {'module__isnull': False}),
            ('name__exact', ['example'], {'name__exact': 'example'}),
            ('name__icontains', ['example'], {'name__icontains': 'example'}),
            ('name__startswith', ['example'], {'name__startswith': 'example'}),
            ('name__regex', ['^example'], {'name__regex': '^example'}),
        ):
            with self.subTest(key=key, values=values):
                parsed = view.parse_model_query_filter(key, values)
                self.assertEqual(parsed, expected)
                view.model.objects.filter(**parsed)

    def test_generic_crud_honors_instance_model_and_custom_exact_fields(self):
        view = ModelCRUD()
        view.model = ApiCaseCRUD.model
        view.not_matching_str = [*view.not_matching_str, 'name']
        self.assertEqual(view.parse_model_query_filter('name', ['example']), {'name': 'example'})
        self.assertEqual(view.parse_model_query_filter('id__range', ['1', '9']), {'id__range': ['1', '9']})

    def test_numeric_related_ranges_do_not_receive_contains(self):
        view = ApiCaseCRUD()
        for key in ('level__lt', 'case_people__id__gte', 'project_product__project__id__lte'):
            with self.subTest(key=key):
                parsed = view.parse_model_query_filter(key, ['3'])
                self.assertEqual(parsed, {key: '3'})
                view.model.objects.filter(**parsed)

    def test_every_affected_list_routes_time_filters_to_shared_parser(self):
        for view_class in (ModelCRUD, *self.views):
            view = view_class()
            view.model = view.model or ApiCaseCRUD.model
            key, value = 'create_time__lt', '2026-11-18T00:00:00+08:00'
            request = Request(RequestFactory().get('/api/example', {key: value}))
            with self.subTest(view=view_class.__name__), patch.object(
                    view_class, 'parse_model_query_filter', side_effect=RuntimeError('shared parser reached')) as parser:
                with self.assertRaisesRegex(RuntimeError, 'shared parser reached'):
                    view_class.get.__wrapped__(view, request)
                parser.assert_called_once_with(key, [value])

    def test_generic_list_keeps_paging_and_data_scope_with_date_range(self):
        view = ModelCRUD()
        view.model = ApiCaseCRUD.model
        view.filter_queryset_by_data_scope = Mock(side_effect=lambda request, queryset: queryset)
        view.list_response = Mock(return_value='query prepared')
        request = Request(RequestFactory().get('/api/example', {
            'create_time__date__range': '2026-11-17,2026-11-18', 'page': '1', 'pageSize': '20'}))
        with patch('src.common.responses.model_crud.import_string') as policy:
            self.assertEqual(ModelCRUD.get.__wrapped__(view, request), 'query prepared')
            policy.return_value.apply_project_context.assert_called_once()
        view.filter_queryset_by_data_scope.assert_called_once()
        queryset = view.list_response.call_args.args[1]
        self.assertEqual(queryset.query.where.children[0].lookup_name, 'range')
        self.assertIs(view.list_response.call_args.args[2], True)
