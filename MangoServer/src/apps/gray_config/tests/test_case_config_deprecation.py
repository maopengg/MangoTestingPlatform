from django.test import SimpleTestCase
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from src.apps.gray_config.api.views.case_config import DeprecatedCaseGrayConfigApiMixin


class DeprecatedCaseGrayConfigApiTests(SimpleTestCase):
    def test_deprecated_headers_are_returned(self):
        class DeprecatedView(DeprecatedCaseGrayConfigApiMixin, APIView):
            def get(self, request: Request):
                return Response({'ok': True})

        response = DeprecatedView.as_view()(APIRequestFactory().get('/api/gray/case-config'))

        self.assertEqual(response['Deprecation'], 'true')
        self.assertIn('deprecated', response['Warning'])
