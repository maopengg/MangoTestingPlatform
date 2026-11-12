from unittest.mock import patch

from django.test import TestCase
from mangotools.enums import TaskEnum

from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.models import Project, ProjectProduct, TestSuite, TestSuiteDetails
from src.apps.test_center.services.reporting.test_suite.stop import TestSuiteStopService
from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService
from src.apps.test_center.services.reporting.test_suite.update_test_suite import UpdateTestSuite
from src.apps.user.models import User


class TestSuiteStopServiceTests(TestCase):
    def setUp(self):
        project = Project.objects.create(name='停止报告项目')
        self.product = ProjectProduct.objects.create(project=project, name='停止报告产品')
        self.user = User.objects.create(
            name='停止报告用户',
            username='report_stop_user',
            password='pwd',
            is_super_admin=True,
        )
        self.suite = TestSuite.objects.create(
            id=41001,
            project_product=self.product,
            test_env=0,
            user=self.user,
            status=TaskEnum.PROCEED.value,
            is_notice=0,
        )
        self.pending_detail = self.create_detail(1, TaskEnum.STAY_BEGIN.value)
        self.running_detail = self.create_detail(2, TaskEnum.PROCEED.value)
        self.completed_detail = self.create_detail(3, TaskEnum.SUCCESS.value)
        self.completed_detail.type = TestCaseTypeEnum.UI.value
        self.completed_detail.success = 1
        self.completed_detail.save(update_fields=['type', 'success'])
        self.running_detail.success = 1
        self.running_detail.fail = 1
        self.running_detail.warning = 1
        self.running_detail.save(update_fields=['success', 'fail', 'warning'])

    def create_detail(self, case_id: int, status: int):
        return TestSuiteDetails.objects.create(
            test_suite=self.suite,
            type=TestCaseTypeEnum.API.value,
            project_product=self.product,
            test_env=0,
            case_id=case_id,
            case_name=f'停止用例{case_id}',
            status=status,
            retry=1,
            case_sum=1,
        )

    @patch.object(TestSuiteStopService, '_notify_actuators', return_value=2)
    def test_stop_marks_only_active_tasks_and_report_stopped(self, notify_actuators):
        result = TestSuiteStopService.stop(self.suite.id)

        self.suite.refresh_from_db()
        self.pending_detail.refresh_from_db()
        self.running_detail.refresh_from_db()
        self.completed_detail.refresh_from_db()
        self.assertEqual(self.suite.status, TaskEnum.STOPPED.value)
        self.assertEqual(self.pending_detail.status, TaskEnum.STOPPED.value)
        self.assertEqual(self.running_detail.status, TaskEnum.STOPPED.value)
        self.assertEqual(self.pending_detail.error_message, TestSuiteStopService.STOP_REASON)
        self.assertEqual(self.running_detail.error_message, TestSuiteStopService.STOP_REASON)
        self.assertEqual(
            (self.running_detail.success, self.running_detail.fail, self.running_detail.warning),
            (0, 0, 0),
        )
        self.assertEqual(self.completed_detail.status, TaskEnum.SUCCESS.value)
        self.assertEqual(result['stopped_details'], 2)
        self.assertEqual(result['notified_actuators'], 2)
        summary = TestSuiteSummaryService.summary_data(self.suite.id)
        self.assertEqual(summary['stopped_count'], 2)
        self.assertEqual(summary['fail_count'], 0)
        notify_actuators.assert_called_once_with(self.suite.id)

    @patch.object(TestSuiteStopService, '_notify_actuators', return_value=0)
    def test_late_status_update_is_ignored_after_stop(self, _notify_actuators):
        TestSuiteStopService.stop(self.suite.id)

        updated = UpdateTestSuite.update_test_suite_details_status(
            self.running_detail.id,
            TaskEnum.SUCCESS.value,
            None,
        )

        self.running_detail.refresh_from_db()
        self.assertFalse(updated)
        self.assertEqual(self.running_detail.status, TaskEnum.STOPPED.value)
        self.assertEqual(self.running_detail.error_message, TestSuiteStopService.STOP_REASON)

    def test_completed_report_cannot_be_stopped(self):
        self.suite.status = TaskEnum.SUCCESS.value
        self.suite.save(update_fields=['status'])

        with self.assertRaises(TestCenterError):
            TestSuiteStopService.stop(self.suite.id)
