from unittest.mock import Mock

from django.db.models import Q, QuerySet
from django.test import SimpleTestCase

from src.apps.test_center.services.test_suite.detail_query import TestSuiteDetailQueryService


class TestSuiteDetailQueryServiceTests(SimpleTestCase):
    def setUp(self):
        self.queryset = Mock(spec=QuerySet)
        self.filtered_queryset = Mock(spec=QuerySet)
        self.queryset.filter.return_value = self.filtered_queryset

    def test_name_uses_fuzzy_search(self):
        queryset = TestSuiteDetailQueryService.filter_by_case_keyword(self.queryset, '登录')

        self.assertIs(queryset, self.filtered_queryset)
        self.queryset.filter.assert_called_once_with(Q(case_name__icontains='登录'))

    def test_numeric_keyword_matches_detail_id_case_id_and_fuzzy_name(self):
        queryset = TestSuiteDetailQueryService.filter_by_case_keyword(self.queryset, '101')

        self.assertIs(queryset, self.filtered_queryset)
        self.queryset.filter.assert_called_once_with(
            Q(case_name__icontains='101') | Q(case_id=101) | Q(id=101)
        )

    def test_empty_keyword_keeps_queryset(self):
        queryset = TestSuiteDetailQueryService.filter_by_case_keyword(self.queryset, '  ')

        self.assertIs(queryset, self.queryset)
        self.queryset.filter.assert_not_called()
