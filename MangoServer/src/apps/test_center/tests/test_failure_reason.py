from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from src.apps.test_center.api.views.test_suite_details import TestSuiteDetailsShareViews
from src.apps.test_center.services.reporting.test_suite.failure_reason import TestSuiteFailureReasonService


class TestSuiteFailureReasonServiceTests(SimpleTestCase):
    def test_failure_reason_endpoint_does_not_require_user_authentication(self):
        self.assertEqual(TestSuiteDetailsShareViews.authentication_classes, [])

    def test_collects_all_failed_children_and_groups_normalized_messages(self):
        details = [
            SimpleNamespace(
                status=0,
                error_message='用例失败',
                summary_data={
                    'children': [
                        {'status': 0, 'error_message': '连接  超时\n请重试'},
                        {'status': 1, 'error_message': '不应统计'},
                    ],
                    'meta': {},
                },
            ),
            SimpleNamespace(
                status=0,
                error_message='连接 超时 请重试',
                summary_data=None,
            ),
        ]
        queryset = MagicMock()
        queryset.only.return_value.iterator.return_value = iter(details)

        with patch(
                'src.apps.test_center.services.reporting.test_suite.failure_reason.TestSuiteDetails.objects.filter',
                return_value=queryset,
        ) as filter_mock:
            result = TestSuiteFailureReasonService.top_failure_reasons(1)

        filter_mock.assert_called_once_with(test_suite_id=1)
        self.assertEqual(result['category_count'], 1)
        self.assertEqual(result['failure_count'], 2)
        self.assertEqual(result['items'][0], {
            'message': '连接 超时 请重试',
            'count': 2,
            'percent': 100,
        })

    def test_uses_status_details_and_limits_top_items(self):
        detail = SimpleNamespace(
            status=0,
            error_message=None,
            summary_data={
                'children': [
                    {'status': 'failed', 'statusDetails': {'message': '断言失败'}},
                    {'status': 'broken', 'message': '环境异常'},
                    {'status': 0},
                ]
            },
        )
        queryset = MagicMock()
        queryset.only.return_value.iterator.return_value = iter([detail])

        with patch(
                'src.apps.test_center.services.reporting.test_suite.failure_reason.TestSuiteDetails.objects.filter',
                return_value=queryset,
        ):
            result = TestSuiteFailureReasonService.top_failure_reasons(1, limit=2)

        self.assertEqual(len(result['items']), 2)
        self.assertEqual(result['category_count'], 3)
