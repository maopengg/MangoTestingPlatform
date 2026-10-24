from django.test import SimpleTestCase

from src.apps.auto_api.api.views.api_case import ApiCaseCRUD


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
