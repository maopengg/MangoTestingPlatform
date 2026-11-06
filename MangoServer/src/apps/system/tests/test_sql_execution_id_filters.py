from unittest.mock import Mock

from django.test import SimpleTestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from src.apps.system.api.views.sql_execution import SqlExecutionRecordViews


class SqlExecutionIdFilterTests(SimpleTestCase):
    def test_comma_separated_ids_use_in_lookup(self):
        request = Request(APIRequestFactory().get('/', {'id__in': '2054,2014'}))
        queryset = Mock()
        filtered = SqlExecutionRecordViews._apply_filters(request, queryset)
        queryset.filter.assert_called_once_with(id__in=[2054, 2014])
        self.assertIs(filtered, queryset.filter.return_value)

    def test_invalid_id_list_does_not_remove_filter(self):
        for value in ['2054,invalid', '2054,-1', '2054,0', ',']:
            request = Request(APIRequestFactory().get('/', {'id__in': value}))
            queryset = Mock()
            self.assertIsNone(SqlExecutionRecordViews._apply_filters(request, queryset))
            queryset.filter.assert_not_called()

    def test_type_multiselect_preserves_mysql_zero_and_redis_es(self):
        request = Request(APIRequestFactory().get('/', {'datasource_type__in': '0,10,20'}))
        queryset = Mock()
        SqlExecutionRecordViews._apply_filters(request, queryset)
        queryset.filter.assert_called_once_with(datasource_type__in=[0, 10, 20])

    def test_invalid_type_collection_is_rejected(self):
        request = Request(APIRequestFactory().get('/', {'datasource_type__in': '0,invalid'}))
        queryset = Mock()
        self.assertIsNone(SqlExecutionRecordViews._apply_filters(request, queryset))
        queryset.filter.assert_not_called()
