from django.test import SimpleTestCase

from src.apps.auto_api.api.views.api_case import ApiCaseCRUD
from src.apps.auto_api.models import ApiCase


class ApiCaseFilterTests(SimpleTestCase):

    def test_parse_comma_separated_module_ids(self):
        self.assertEqual(
            ApiCaseCRUD.parse_query_filter('module__in', ['1,2', '3']),
            {'module__in': ['1', '2', '3']},
        )

    def test_parse_exact_and_contains_filters(self):
        self.assertEqual(ApiCaseCRUD.parse_query_filter('level', ['0']), {'level': '0'})
        self.assertEqual(
            ApiCaseCRUD.parse_query_filter('name', ['租户']),
            {'name__contains': '租户'},
        )

    def test_time_comparison_does_not_append_contains_record_372(self):
        for field in ('create_time', 'update_time'):
            for lookup in ('lt', 'lte', 'gt', 'gte'):
                key = f'{field}__{lookup}'
                with self.subTest(key=key):
                    parsed = ApiCaseCRUD.parse_query_filter(key, ['2026-11-18T00:00:00+08:00'])
                    self.assertEqual(parsed, {key: '2026-11-18T00:00:00+08:00'})
                    # ORM 构造即可复现原 FieldError，不查询业务数据库。
                    queryset = ApiCase.objects.filter(**parsed)
                    self.assertEqual(queryset.query.where.children[0].lookup_name, lookup)

    def test_explicit_text_lookup_is_not_wrapped_in_another_contains(self):
        for key in ('name__exact', 'name__icontains', 'name__startswith', 'name__contains'):
            with self.subTest(key=key):
                self.assertEqual(ApiCaseCRUD.parse_query_filter(key, ['example']), {key: 'example'})

    def test_numeric_range_and_date_transform_are_preserved(self):
        for key, values, expected in (
            ('level__gte', ['1'], {'level__gte': '1'}),
            ('level__range', ['1,3'], {'level__range': ['1', '3']}),
            ('create_time__date__range', ['2026-11-17', '2026-11-18'],
             {'create_time__date__range': ['2026-11-17', '2026-11-18']}),
            ('create_time__year__gte', ['2026'], {'create_time__year__gte': '2026'}),
        ):
            with self.subTest(key=key):
                parsed = ApiCaseCRUD.parse_query_filter(key, values)
                self.assertEqual(parsed, expected)
                ApiCase.objects.filter(**parsed)

    def test_empty_filters_keep_existing_api_case_semantics(self):
        for values in ([], [None], [''], ['null'], ['undefined']):
            with self.subTest(values=values):
                self.assertEqual(ApiCaseCRUD.parse_query_filter('name', values), {})
        self.assertEqual(ApiCaseCRUD.parse_query_filter('module__in', ['']), {})
