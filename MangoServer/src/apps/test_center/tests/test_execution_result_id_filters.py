from django.test import SimpleTestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from src.apps.test_center.api.views.execution_result import ExecutionResultViews


class ExecutionResultIdFilterTests(SimpleTestCase):
    def test_multiple_ids_keep_existing_filters(self):
        request = Request(APIRequestFactory().get('/', {'id__in': '2054,2014', 'status': '1'}))
        filters = ExecutionResultViews.build_admin_filters(request)
        self.assertEqual(filters['id__in'], [2054, 2014])
        self.assertEqual(filters['status'], 1)

    def test_invalid_ids_are_rejected(self):
        for value in ['2054,invalid', ',']:
            request = Request(APIRequestFactory().get('/', {'id__in': value}))
            self.assertIsNone(ExecutionResultViews.build_admin_filters(request))
