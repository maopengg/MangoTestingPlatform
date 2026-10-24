from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from mangotools.enums import TaskEnum

from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.services.test_suite.retry import TestSuiteRetryService


class RetryFailedReportTests(SimpleTestCase):
    def setUp(self):
        self.suite = SimpleNamespace(id=10, status=TaskEnum.FAIL.value)
        self.details = [
            SimpleNamespace(id=1, status=TaskEnum.FAIL.value, fail=1),
            SimpleNamespace(id=2, status=TaskEnum.SUCCESS.value, fail=0),
            SimpleNamespace(id=3, status=TaskEnum.WARNING.value, fail=0),
            SimpleNamespace(id=4, status=TaskEnum.SUCCESS.value, fail=2),
        ]
        for detail in self.details:
            detail.is_excluded = False
        for name, target in (
                ('suites', 'TestSuite.objects'), ('rows', 'TestSuiteDetails.objects'),
        ):
            item = patch(f'src.apps.test_center.services.test_suite.retry.{target}')
            setattr(self, name, item.start())
            self.addCleanup(item.stop)
        atomic = patch('src.apps.test_center.services.test_suite.retry.transaction.atomic', side_effect=nullcontext)
        atomic.start()
        self.addCleanup(atomic.stop)
        self.suites.select_for_update.return_value.filter.return_value.first.side_effect = lambda: self.suite
        self.rows.select_for_update.return_value.filter.return_value.__iter__.side_effect = lambda: iter(self.details)

    def test_only_failed_execution_items_retry_using_existing_detail_logic(self):
        with patch.object(TestSuiteRetryService, 'retry_detail') as retry:
            self.assertEqual(TestSuiteRetryService.retry_failed(10), 2)
        self.assertEqual([call.args[0] for call in retry.call_args_list], [1, 4])
        values = self.suites.filter.return_value.update.call_args.kwargs
        self.assertEqual(values['status'], TaskEnum.STAY_BEGIN.value)
        self.assertNotIn('test_env', values)
        self.assertNotIn('api_concurrency_limit', values)

    def test_no_failure_leaves_report_untouched(self):
        self.details = self.details[1:3]
        with patch.object(TestSuiteRetryService, 'retry_detail') as retry:
            self.assertEqual(TestSuiteRetryService.retry_failed(10), 0)
        retry.assert_not_called()
        self.suites.filter.return_value.update.assert_not_called()

    def test_failed_retry_skips_excluded_items(self):
        self.details[0].is_excluded = True
        with patch.object(TestSuiteRetryService, 'retry_detail') as retry:
            self.assertEqual(TestSuiteRetryService.retry_failed(10), 1)
        retry.assert_called_once_with(4)

    def test_running_report_or_detail_blocks_duplicate_retry(self):
        for report_running in (True, False):
            with self.subTest(report_running=report_running):
                self.suite.status = TaskEnum.PROCEED.value if report_running else TaskEnum.FAIL.value
                self.details[1].status = TaskEnum.SUCCESS.value if report_running else TaskEnum.STAY_BEGIN.value
                with patch.object(TestSuiteRetryService, 'retry_detail') as retry:
                    with self.assertRaises(TestCenterError):
                        TestSuiteRetryService.retry_failed(10)
                retry.assert_not_called()

    def test_missing_report_is_rejected(self):
        self.suite = None
        with self.assertRaises(TestCenterError):
            TestSuiteRetryService.retry_failed(10)
